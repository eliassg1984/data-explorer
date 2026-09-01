"""
graficos.base — infraestructura compartida por todos los dashboards de gráficos.

Helpers reutilizables (cards nativos, motor genérico config-driven, resolución
de columnas, formato de ejes/hover). NO contiene ningún dashboard concreto:
cada dashboard (ajuste.py, compras.py, ...) importa lo que necesita de aquí.
"""

import datetime
import re
import unicodedata
from contextlib import contextmanager

import pandas as pd
import plotly.express as px
import html
import json

import streamlit as st

import navegacion
from inyecciones._iframe import inyectar_html

from navegacion import _CSS_FRANJA_VISTAS
from utils import buscar_columna, _norm
from tema import (
    BLANCO, ESCALA_CONTINUA, GRIS_BORDE, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
    PALETA_SERIES,
)
from cortes import MESES_ABR_ES
from estado_rango import (ESCALAS, aplicar_atajo, escala_a_rango,
                          escala_desde_rango, escala_periodos, ventana_ano,
                          ventana_decada, ventana_mes)
from graficos import alturas


def _slug(texto):
    """Convierte un texto a un identificador válido para keys/CSS."""
    return re.sub(r"\W+", "_", str(texto)).strip("_").lower()


def _slug_url(texto):
    """Como `_slug` pero SIN acentos — es lo que viaja en `?vista=`, para que
    la URL se pueda tipear a mano ("comparativo_vs_ano_pasado" y no
    "comparativo_vs_año_pasado", que en la barra sale percent-encodeado).

    NO se toca `_slug`: ese alimenta las keys de los widgets y por lo tanto
    los selectores de `estilos/` — cambiarlo movería CSS de sitio.
    Para LEER el parámetro no se usa esto sino `_norm`, que además ignora
    separadores: así entra igual "Año Pasado" que "ano-pasado"."""
    ascii_ = (unicodedata.normalize("NFKD", str(texto))
              .encode("ascii", "ignore").decode())
    return re.sub(r"\W+", "_", ascii_).strip("_").lower()


def _es_movil():
    """True si el request viene de un teléfono/tablet, leyendo el User-Agent
    del header (server-side, sin JS ni rerun). Se usa para decisiones que
    Plotly dibuja en el servidor y no puede adaptar al ancho real de pantalla
    (p. ej. cuánto abreviar los nombres sobre las barras, o si un heatmap
    ancho se renderiza a su tamaño completo y se scrollea en vez de achicarse
    hasta ser ilegible). Ante la duda (sin header o UA raro) asume desktop,
    que es el caso con más espacio. Cacheado por sesión.

    Vivía en graficos/compras/_comun.py (nació ahí para las etiquetas de
    barra de Proveedor) — se movió acá el 2026-08-07 al necesitarlo también
    graficos/ajuste.py para el mapa de calor: es infraestructura compartida,
    no algo propio de Compras. compras/_comun.py reexporta este mismo símbolo
    para no romper sus imports existentes."""
    _c = st.session_state.get("_es_movil_cache")
    if _c is not None:
        return _c
    try:
        ua = (st.context.headers.get("User-Agent", "") or "").lower()
    except Exception:
        ua = ""
    _m = any(k in ua for k in ("mobile", "android", "iphone", "ipad", "ipod"))
    st.session_state["_es_movil_cache"] = _m
    return _m


def _rail_set(state_key, opcion_id):
    """Callback de los botones del rail: fija la selección ANTES del rerun."""
    st.session_state[state_key] = opcion_id


def publicar_contexto_ia(reporte, df, filtros=None):
    """Publica el df EFECTIVO (con los chips ya aplicados) para el asistente IA.

    POR QUÉ existe: `app.py` llama a `inject_asistente(df_contexto=df_f)`, y
    `df_f` está filtrado por FECHA pero NO por los chips Área/Familia/etc —
    esos se aplican sobre una copia local dentro de cada dashboard (ver
    `graficos/ajuste/__init__.py`, misma trampa que la regla #58 con
    `df_full`). Resultado: el usuario filtraba a un área, preguntaba "¿cuál
    es el total?" y el asistente respondía el total SIN filtrar,
    contradiciendo lo que había en pantalla.

    Cada dashboard llama a esto justo DESPUÉS de aplicar sus chips. Funciona
    por el orden de `app.py`: `_render_contenido()` corre antes de
    `inject_asistente()`, así que lo publicado acá ya está disponible.

    Se guarda el nombre del reporte junto al df A PROPÓSITO: si el usuario
    cambia de reporte y el dashboard nuevo no publica (porque no tiene
    chips), el asistente detecta que el contexto es de OTRO reporte y cae al
    `df_f` que le pasa app.py, en vez de responder con datos del reporte
    anterior. Sin ese chequeo, un contexto viejo sobrevive en session_state
    y miente en silencio.

    `filtros` es un dict {etiqueta: valor(es)} solo para CONTARLE al modelo
    qué está filtrado; el filtrado real ya viene hecho en `df`.
    """
    st.session_state["_ia_contexto"] = {
        "reporte": reporte,
        "df": df,
        "filtros": {k: v for k, v in (filtros or {}).items() if v},
    }


# ===========================================================================
# COMPARTIMENTO DE FILTROS — un solo control en la franja de vistas
# ===========================================================================
# Hasta el 2026-08-31 cada reporte dibujaba su propia FILA de chips dentro de
# `chips_ajuste_tabla`: un `st.popover` por columna filtrable, uno al lado del
# otro. Eran SIETE copias del mismo bloque (`app.py` x2 — tabla y Ajuste — mas
# los seis dashboards) y la fila crecia con cada filtro nuevo: Ajuste y Ventas
# ya iban por cuatro.
#
# Ahora es UN popover, a la derecha de la franja de vistas y separado de las
# pestanas por un filete: un compartimento de esa misma superficie, no una
# capsula apoyada encima. La geometria vive en `estilos/_50_fecha.py` (la
# regla con la clase duplicada, que es la que gana).
#
# LA RESTRICCION QUE MANDA EL DISENO: Streamlit no anida popovers. Los filtros
# de adentro dejan de ser popovers y pasan a ser secciones planas — rotulo +
# pills, via `filtro_pills()`. No es una concesion: es justo lo que se pidio,
# una sola lista desplegable en vez de tres que se abren por su cuenta.

def contar_filtros(*claves, neutro="Todos"):
    """Cuantos de esos filtros tienen algo puesto, leido de `session_state`.

    Va ANTES de dibujar el compartimento porque su etiqueta lleva la cuenta y
    Streamlit la fija al construir el widget. Es el mismo patron que ya usaba
    cada chip por separado (`len(st.session_state.get(k) or [])`), sumado.

    Distingue las dos formas que hay en el repo sin pedir un parametro por
    sitio: una LISTA cuenta si no esta vacia (multiseleccion), y un STRING
    cuenta si no es el valor neutro (los chips de opcion unica de Ajuste, que
    en reposo dicen "Todos").
    """
    n = 0
    for clave in claves:
        valor = st.session_state.get(clave)
        if isinstance(valor, str):
            n += 1 if valor != neutro else 0
        elif valor:
            n += 1
    return n


@contextmanager
def compartimento_filtros(n_activos=0, etiqueta="Filtros"):
    """El compartimento de filtros de la franja: UN popover a su derecha.

    `n_activos` sale de `contar_filtros()` y se pinta como badge — es lo unico
    que tiene que gritar, porque con el panel cerrado no se ve que hay puesto.

    El wrapper `chipwrap_filtros_on|off` no es decorativo: es el mismo
    contrato de key que ya usaban los chips sueltos, asi que el estado activo
    (subrayado de acento, `estilos/_50_fecha.py`) se hereda sin escribir una
    regla nueva.
    """
    _lbl = (f":material/filter_alt: {etiqueta} :violet-badge[{n_activos}]"
            if n_activos else f":material/filter_alt: {etiqueta}")
    with st.container(key="chips_ajuste_tabla"):
        with st.container(key=f"chipwrap_filtros_{'on' if n_activos else 'off'}"):
            with st.popover(_lbl, use_container_width=True):
                yield


def filtro_pills(df, col, clave, etiqueta, valores=None):
    """Un filtro categorico PLANO, para adentro de `compartimento_filtros()`.

    Devuelve `(df_filtrado, seleccion)`, el mismo contrato que tenian los
    chips-popover que reemplaza. Sin popover propio: rotulo + pills, porque
    Streamlit no anida popovers (ver el comentario de arriba).

    `valores` permite pasar una lista ya calculada — lo necesitan las cascadas
    (Subfamilia depende de Familia), donde las opciones no salen del df que se
    esta filtrando sino de uno ya recortado por el filtro de arriba.
    """
    if not col or col not in df.columns:
        return df, []
    if valores is None:
        valores = sorted(df[col].dropna().astype(str).unique().tolist())
    if not valores:
        return df, []
    st.markdown(f'<div class="filtro-rotulo">{html.escape(etiqueta)}</div>',
                unsafe_allow_html=True)
    sel = st.pills(etiqueta, valores, selection_mode="multi",
                   key=clave, label_visibility="collapsed") or []
    if sel:
        df = df[df[col].astype(str).isin(sel)]
    return df, sel


def vista_activa(categorias, state_key):
    """Que item del rail esta activo, SIN dibujarlo.

    Existe para `app.py`: la franja superior se dibuja en la linea ~500 y
    el rail recien en `_render_contenido()`, mas de 600 lineas despues, asi
    que cuando la franja tiene que decidir su layout todavia no sabe que
    vista eligio el usuario. Leer `session_state` a secas no alcanza: en la
    PRIMERA carga de un deep-link (`?vista=...`) la clave aun no existe —la
    siembra `_render_rail`— y la franja se dibujaria una vez con el layout
    equivocado antes de corregirse. Eso es un parpadeo visible.

    Resuelve con el MISMO criterio que `_render_rail` (y llamada por el,
    para que no haya dos copias que se puedan desincronizar): lo guardado
    si sigue siendo valido, si no el `?vista=` de la URL normalizado, si no
    el primer item.
    """
    _todos = [item[0] for _, items in categorias for item in items]
    if not _todos:
        return None
    sel = st.session_state.get(state_key)
    if sel in _todos:
        return sel
    _por_norm = {_norm(o): o for o in _todos}
    return _por_norm.get(_norm(st.query_params.get("vista", ""))) or _todos[0]


def _activar_seccion(clave):
    """Callback del botón invisible que dispara el observador de JS."""
    st.session_state[f"_pila_activa_{clave}"] = True


@st.fragment
def seccion_perezosa(clave, vista, dibujar, activa_de_entrada=False):
    """Una sección de una página apilada: esqueleto hasta que te acercás.

    ESTO ES LO QUE HACE VIABLE LA PILA. Dibujar las seis secciones de una
    satura el hilo principal del navegador montando ~10 figuras Plotly y dos
    AgGrid a la vez: en Streamlit Cloud el navegador llegó a mostrar "la
    página no responde" (2026-08-25, revert 02b6b58). El servidor no era el
    problema — Streamlit ya manda cada elemento apenas lo termina, así que el
    contenido bajaba de arriba abajo. Lo que se saturaba era el CLIENTE.

    La solución es la que usan los dashboards que hacen esto bien. Medido en
    MSN Dinero el 2026-08-25, recién cargado y después de bajar:

        secciones "Cargando…"      6  →  0
        SVG en el DOM             42  → 113
        alto de página        1.812px → 7.631px

    O sea: no dibujan lo de abajo hasta que te acercás.

    CÓMO SE HACE ACÁ, que es lo que no era obvio: `@st.fragment` tiene rerun
    AISLADO — tocar un widget de adentro re-ejecuta ese fragment y nada más.
    Eso es lo que vuelve barato activar una sección: no se reconstruyen las
    otras cinco. (Se descartó este camino una vez razonando sobre reruns
    completos, que sí serían cuadráticos; el error fue olvidar los fragments.)

    El disparador es un botón invisible que el temporizador de
    `_render_rail` APRIETA cuando la sección se acerca — 900px antes de que
    asome, para que llegue dibujada y no se vea el esqueleto de paso.

    `activa_de_entrada` la usa la primera sección: arrancar con todo en
    esqueleto dejaría la página vacía al abrir.
    """
    k = f"_pila_activa_{clave}"
    if activa_de_entrada:
        st.session_state[k] = True

    if not st.session_state.get(k, False):
        st.markdown(esqueleto_pila(vista), unsafe_allow_html=True)
        # `on_click` y no el valor de retorno: con el callback el estado ya
        # está puesto cuando el fragment se re-ejecuta, así que la sección se
        # dibuja en ESA pasada. Leyendo el return haría falta un rerun más.
        st.button("cargar", key=f"pila_go_{clave}",
                  on_click=_activar_seccion, args=(clave,))
        return

    dibujar()


def scroll_a_seccion(clave):
    """Lleva la vista a la sección `clave` de una página APILADA.

    Los botones del rail ya scrollean solos (el JS de `_render_rail`
    intercepta el clic antes de que Streamlit lo vea), pero un botón
    cualquiera de ADENTRO de la página no pasa por ahí — hoy el
    "Abrir Sankey →" del Panorama de Recetas. Antes esos botones escribían
    el `state_key` del rail y hacían `st.rerun()`, que con la pila ya no
    lleva a ningún lado: el rail dejó de ELEGIR contenido y pasó a MARCAR
    dónde estás, así que setear su clave sólo enciende un botón.

    Se llama DESDE el `if st.button(...)`, o sea una sola vez, en el run
    siguiente al clic. Reintenta como el resto del JS del proyecto: el
    `<script>` vive en un iframe que carga en paralelo al resto de la
    página (ver `_arrastrar_ventana_riel`). Y no importa que la sección
    destino esté todavía en esqueleto: el contenedor con la key es el
    mismo, así que el scroll llega igual y el `IntersectionObserver` del
    rail se encarga de construirla al acercarse.
    """
    inyectar_html(f"""<script>
    (function () {{
      var w = window.parent, doc = w.document, intentos = 0;
      function ir() {{
        intentos++;
        var el = doc.querySelector('[class*="st-key-{clave}"]');
        if (!el) {{ if (intentos < 20) w.setTimeout(ir, 100); return; }}
        el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
      }}
      ir();
    }})();
    </script>""")


def esqueleto_pila(nombre):
    """HTML del hueco que ocupa una sección mientras se construye.

    Lo consume una página APILADA (hoy Compras): se dibujan los seis huecos
    de una, y después cada sección real reemplaza al suyo. Así la página
    nace con su estructura y su altura en vez de crecer bajo el cursor, y
    cada hueco dice qué vista va a ocupar — o sea que sirve de índice de lo
    que viene mientras carga.

    Vale la pena porque construir la pila cuesta ~45s en una máquina lenta
    (cache de datos caliente; ~118s en frío). Streamlit ya manda cada
    elemento apenas lo termina, así que la PRIMERA sección se puede leer
    enseguida; lo que faltaba era que se notara que abajo viene más.

    El aspecto (altura reservada, brillo, movimiento reducido) vive en
    `estilos/_27_pila.py`. Acá sólo va la forma.
    """
    return (
        '<div class="pila-hueco">'
        f'<div class="pila-hueco-tit">{nombre}</div>'
        '<div class="pila-hueco-barra"></div>'
        '<div class="pila-hueco-caja"></div>'
        '</div>'
    )


def _fmt_periodo(escala, d):
    """Etiqueta de una parada del riel. Corta: entran ~12 en 250px."""
    if escala == "Años":
        return str(d.year)
    return f"{MESES_ABR_ES[d.month - 1]} {d.year % 100:02d}"


def _aplicar_escala(k_riel, escala, ctx, bandera):
    """`on_change` del riel: traduce el par de períodos y lo aplica.

    Por qué CALLBACK y no cuerpo: `ctx["k_rango"]` es la key del
    `st.date_input` que `app.py` ya instanció en este mismo run, y escribir
    la clave de un widget ya instanciado es `StreamlitAPIException`. El
    callback corre ANTES del rerun, que es el único momento en que la
    escritura es legal. Mismo motivo (y mismo bug) que
    `graficos/compras/proveedor.py::_aplicar_atajo_rank`; es literalmente lo
    que rompió la vista Semanal en la fusión del 2026-08-24.

    `bandera` la consume el fragment que dibuja el riel para escalar a
    `st.rerun(scope="app")`: el filtro que lee el rango vive FUERA del
    fragment, así que sin escalada el estado cambia y la pantalla no.
    """
    par = st.session_state.get(k_riel)
    if not (par and len(par) == 2):
        return
    aplicar_atajo(ctx["k_rango"],
                  escala_a_rango(escala, par[0], par[1],
                                 (ctx["fecha_min"], ctx["fecha_max"])),
                  ctx["reporte"], ctx["usa_carga_rango"])
    if bandera:
        st.session_state[bandera] = True


# Qué VENTANA usa cada escala. Cada una mira UN período de la escala de
# arriba: Días mira un mes, Meses mira un año, Años mira una década. Las
# tres se explican con la misma frase, que es justo lo que se pidió al
# sumar la tercera (2026-08-26, "cuando es años, también debe seguir la
# lógica de mostrar sólo años").
_VENTANA_DE_ESCALA = {"Días": ventana_mes,
                      "Meses": ventana_ano,
                      "Años": ventana_decada}


def _rotulo_ventana(escala, ventana):
    """Lo que dice la cabecera entre las flechas: el mes en Días, el año en
    Meses, el tramo de años en Años. Mayúscula y espaciado copian la
    captura del selector de Excel que motivó todo esto ("AGO 2026").

    En Años se rotula el tramo REAL de la ventana ya recortada a los datos
    ("2023-2026"), no la década nominal ("2020-2029"): mismo criterio que
    `escala_periodos` con el año del borde — no prometer períodos que no
    tienen nada adentro. Si la ventana cae entera en un año, se dice ese
    año y listo, sin el guión."""
    if escala == "Días":
        return (f"{MESES_ABR_ES[ventana[0].month - 1].upper()} "
                f"{ventana[0].year}")
    if escala == "Años":
        if ventana[0].year == ventana[1].year:
            return str(ventana[0].year)
        return f"{ventana[0].year}-{ventana[1].year}"
    return str(ventana[0].year)


def _ir_a_ventana(ancla, ctx, bandera, escala):
    """`on_click` de las flechas ‹ ›: corre la ventana visible del riel.

    Escribe la VENTANA ENTERA (el mes en Días, el año en Meses, recortada a
    los datos) en la clave canónica — ver `_nav_ventana` para por qué
    SELECCIONA y no sólo mira. Callback y no cuerpo por el motivo de
    siempre: `ctx["k_rango"]` es la key de un widget ya instanciado en este
    run (`_aplicar_escala` lo explica largo).
    """
    _fn = _VENTANA_DE_ESCALA.get(escala)
    if not _fn:
        return
    win = _fn(ancla, (ctx["fecha_min"], ctx["fecha_max"]))
    if not win:
        return
    aplicar_atajo(ctx["k_rango"], win, ctx["reporte"], ctx["usa_carga_rango"])
    if bandera:
        st.session_state[bandera] = True


def _nav_ventana(clave, escala, ventana, bounds, ctx, bandera):
    """Cabecera del riel: ‹ AGO 2026 › en Días, ‹ 2026 › en Meses.

    Copia el gesto de la captura del pedido (selector de fecha de Excel,
    2026-08-26): la ventana visible rotulada en el medio y una flecha a
    cada lado para ir a la anterior/siguiente. Las flechas se DESHABILITAN
    en los bordes de `bounds` en vez de esconderse, así el ancho de la fila
    no salta al llegar al extremo del histórico.

    IR A OTRA VENTANA LA SELECCIONA ENTERA, no sólo corre la vista. En
    Excel la barra de scroll separa las dos cosas; acá no puede: el valor
    de un `st.slider`/`st.select_slider` tiene que caer DENTRO de sus
    límites, o sea que una vista sin selección adentro no se puede
    representar. Seleccionar la ventana entera es además exactamente lo que
    ya hacía la escala "Meses" con un clic — mismo idioma, no uno nuevo.

    Sirve a las DOS escalas con ventana (Días mira un mes, Meses mira un
    año) porque el gesto es el mismo y lo único que cambia es el rótulo y
    qué función recorta — ver `_VENTANA_DE_ESCALA` y `_rotulo_ventana`. Las
    keys de los botones no llevan la escala: sólo se dibuja una a la vez.

    Sin `help=` a propósito: los glifos ya se explican solos, y este mismo
    popover se comió DOS bugs de íconos de ayuda duplicados el 2026-08-25
    (un `help=` del desplegable de atajos y otro del caption de fecha, cada
    uno anclado a la misma esquina).
    """
    _prev = ventana[0] - datetime.timedelta(days=1)
    _sig = ventana[1] + datetime.timedelta(days=1)
    # columnas-internas: fila de tres piezas DENTRO del popover (flecha,
    # rótulo, flecha). No es una fila de drill: COLUMNAS_DRILL no aplica.
    c_izq, c_mes, c_der = st.columns([1, 5, 1], vertical_alignment="center")
    with c_izq:
        st.button("‹", key=f"{clave}_mes_prev", disabled=_prev < bounds[0],
                  on_click=_ir_a_ventana, args=(_prev, ctx, bandera, escala))
    with c_mes:
        st.markdown(f'<div class="cp-riel-mes">'
                    f'{_rotulo_ventana(escala, ventana)}</div>',
                    unsafe_allow_html=True)
    with c_der:
        st.button("›", key=f"{clave}_mes_sig", disabled=_sig > bounds[1],
                  on_click=_ir_a_ventana, args=(_sig, ctx, bandera, escala))


def _us_de(d):
    """Fecha -> microsegundos desde época UTC, EXACTAMENTE como codifica
    `st.slider` sus valores internos para un slider de fechas (verificado
    en el DOM: 2023-01-01 vale 1672531200000000). Hace falta para leer los
    dos tiradores nativos desde JS en su propio idioma."""
    return int(datetime.datetime(
        d.year, d.month, d.day, tzinfo=datetime.timezone.utc
    ).timestamp() * 1_000_000)


def _fecha_de_us(us):
    """Inversa de `_us_de`: microsegundos -> `date`. La usa el relevo
    (`_aplicar_pan_riel`) para volver del número que manda el JS a algo
    que `aplicar_atajo` entiende."""
    return (datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            + datetime.timedelta(microseconds=us)).date()


def _aplicar_pan_riel(k_relevo, ctx, bandera):
    """`on_change` del relevo oculto que arma `_arrastrar_ventana_riel`.

    Por qué un widget de RELEVO y no escribirle directo a los dos
    `<input type="range">` del slider nativo: SE INTENTÓ (2026-08-26,
    primera vuelta) y falla de una forma sutil. `i2.min` está atado al
    valor VIGENTE de `i1` (así el navegador impide que los tiradores se
    crucen), así que había que escribir uno, esperar a que Streamlit
    reaccionara, y RECIÉN AHÍ escribir el otro. Medido: el primer
    `dispatchEvent` ya alcanza a disparar el `on_change` de Streamlit
    —que aplica el atajo y escala a `st.rerun(scope="app")`— ANTES de que
    el segundo `fijar()` llegara a correr; el segundo tirador terminaba
    escribiendo sobre un slider que Streamlit ya había reemplazado por
    otro (nueva `key`, nuevo DOM), sin ningún efecto. Resultado real:
    "01/08/26 – 24/08/26" arrastrado 280 días atrás terminaba en
    "25/10/25 – 01/08/26" — el string SE CORRIÓ, pero el segundo valor
    quedó pegado al primero viejo en vez de haberse corrido igual.

    Un solo widget no tiene ese problema: no hay un segundo tirador con
    un límite dinámico que perseguir. `k_relevo` es un `st.text_input`
    invisible (mismo patrón que `pila_go_`, `estilos/_27_pila.py`) que
    JS llena con `"us_inicio,us_fin"` y dispara UNA sola vez al soltar.

    SEGUNDA TRAMPA, en el mismo día: escribir el valor y disparar
    `input`/`change` no alcanza para que ESTE `on_change` corra —medido:
    el DOM mostraba el string puesto, pero cero rastro en el servidor,
    ni con un `blur()` después. `st.text_input` (react-aria) sólo
    confirma con un Enter de teclado de verdad (`keydown`+`keyup` con
    `key:'Enter'`) o perdiendo el foco de la forma que react-aria
    reconoce — blur programático en un input oculto fuera de pantalla no
    cuenta. El JS de `_arrastrar_ventana_riel` hace foco + valor + Enter,
    en ese orden."""
    raw = st.session_state.get(k_relevo, "")
    try:
        _us1, _us2 = (int(p) for p in raw.split(","))
    except (ValueError, AttributeError):
        return
    aplicar_atajo(ctx["k_rango"], (_fecha_de_us(_us1), _fecha_de_us(_us2)),
                  ctx["reporte"], ctx["usa_carga_rango"])
    if bandera:
        st.session_state[bandera] = True


def _arrastrar_ventana_riel(k_riel, k_relevo, limites):
    """Arrastrar la SELECCIÓN completa del riel de Días, sin cambiar su
    ancho — "como el slider de Excel" (a pedido, 2026-08-26).

    El `st.slider` nativo sólo deja mover un tirador por vez (cambia dónde
    empieza O dónde termina la selección). Elegir una ventana angosta lejos
    del extremo actual son dos arrastres: achicar un lado y después
    caminar el otro. Esto agrega un TERCER gesto — agarrar el tramo
    coloreado del medio y correrlo — sin tocar los dos tiradores nativos,
    que siguen funcionando igual que siempre.

    CÓMO: no se toca el DOM interno de Streamlit para los tiradores (los
    nombres de clase son hashes de emotion, cambian entre builds). Se
    agrega un `<div>` PROPIO, invisible, del ancho exacto de la selección
    actual, como hijo del track (que ya es `position:relative`, así que un
    hijo `position:absolute` cae en el lugar correcto sin cálculo propio de
    coordenadas). Mientras se arrastra, el feedback es puramente visual
    (mover el propio overlay); recién al SOLTAR se escribe UNA vez el
    widget de relevo (`_aplicar_pan_riel` — ver ahí por qué no son los
    dos `<input>` nativos).

    `limites` son los del RIEL, que desde el 2026-08-26 es la ventana de un
    mes y ya no todo el histórico (ver `ventana_mes`). El arrastre topa ahí
    a propósito: cruzar de mes es el trabajo de las flechas ‹ › de
    `_nav_ventana`, igual que en Excel, donde el gesto de arrastrar tampoco
    saca la selección de la franja visible. Dejarlo pasar de largo haría
    que un tirón de 5px al borde saltara de mes sin avisar."""
    _bmin_us, _bmax_us = _us_de(limites[0]), _us_de(limites[1])
    inyectar_html(f"""<script>
    (function () {{
      var w = window.parent, doc = w.document;
      var BMIN = {_bmin_us}, BMAX = {_bmax_us}, DIA = 86400000000;

      // REINTENTAR hasta que el DOM exista, mismo motivo que el scrollspy
      // de `_render_rail`: el `<script>` corre dentro de un IFRAME propio
      // (regla del proyecto: `st.markdown` no ejecuta `<script>`), que
      // carga en paralelo al resto de la página — no hay garantía de que
      // el `st.text_input` de relevo (dibujado por Python JUSTO ANTES,
      // pero montado por React en su propio tiempo) ya esté en el DOM
      // cuando este script arranca. Medido: sin el reintento, el primer
      // chequeo llegaba con el slider YA montado pero el relevo todavía
      // no — un intento único se rendía para siempre en ESE render (el
      // próximo intento sólo llega si el rango vuelve a cambiar, porque
      // `k_riel` es la firma). 20 intentos de 100ms = 2s de margen.
      var intentos = 0;
      function intentar() {{
        intentos++;
        var raiz = doc.querySelector('[class*="st-key-{k_riel}"]');
        var relevo = doc.querySelector(
          '[class*="st-key-{k_relevo}"] input');
        if (!raiz || !relevo) {{
          if (intentos < 20) w.setTimeout(intentar, 100);
          return;
        }}
        var inputs = raiz.querySelectorAll('input[type="range"]');
        if (inputs.length !== 2) return;
        var i1 = inputs[0], i2 = inputs[1];
        var track = i1.closest('[data-orientation="horizontal"]');
        if (!track || track.__panAdjunto) return;
        track.__panAdjunto = true;
        adjuntar(i1, i2, track, relevo);
      }}
      intentar();

      function adjuntar(i1, i2, track, relevo) {{
      var setterInput = w.Object.getOwnPropertyDescriptor(
        w.HTMLInputElement.prototype, 'value').set;

      function pct(us) {{ return (us - BMIN) / (BMAX - BMIN) * 100; }}

      var v1_0 = parseFloat(i1.value), v2_0 = parseFloat(i2.value);
      var overlay = doc.createElement('div');
      overlay.style.cssText = 'position:absolute;top:0;bottom:0;'
        + 'left:' + pct(v1_0) + '%;width:' + (pct(v2_0) - pct(v1_0))
        + '%;cursor:grab;background:transparent;transition:background .12s;';
      track.appendChild(overlay);
      var arrastrando = false, x0 = 0, w0 = 0, nv1 = v1_0, nv2 = v2_0;

      overlay.addEventListener('mouseenter', function () {{
        if (!arrastrando) overlay.style.background = 'rgba(108,92,231,0.14)';
      }});
      overlay.addEventListener('mouseleave', function () {{
        if (!arrastrando) overlay.style.background = 'transparent';
      }});
      overlay.addEventListener('pointerdown', function (ev) {{
        arrastrando = true;
        x0 = ev.clientX;
        w0 = track.getBoundingClientRect().width;
        nv1 = v1_0; nv2 = v2_0;
        overlay.style.cursor = 'grabbing';
        // `setPointerCapture` puede tirar `NotFoundError` si el navegador
        // no reconoce un puntero activo con ese id (medido: pasa con
        // eventos sintéticos al probar, pero es defensivo por las dudas
        // real también) — sin el try/catch, la excepción corta acá el
        // handler y `ev.preventDefault()` de abajo nunca corre.
        try {{ overlay.setPointerCapture(ev.pointerId); }} catch (e) {{}}
        ev.preventDefault();
      }});
      overlay.addEventListener('pointermove', function (ev) {{
        if (!arrastrando || !w0) return;
        var dUs = Math.round((ev.clientX - x0) / w0 * (BMAX - BMIN) / DIA)
          * DIA;
        var a = v1_0 + dUs, b = v2_0 + dUs;
        if (a < BMIN) {{ dUs += (BMIN - a); a = BMIN; b = v2_0 + dUs; }}
        if (b > BMAX) {{ dUs -= (b - BMAX); b = BMAX; a = v1_0 + dUs; }}
        nv1 = a; nv2 = b;
        overlay.style.left = pct(nv1) + '%';
        overlay.style.width = (pct(nv2) - pct(nv1)) + '%';
      }});
      function soltar(ev) {{
        if (!arrastrando) return;
        arrastrando = false;
        overlay.style.background = 'transparent';
        if (nv1 === v1_0 && nv2 === v2_0) return;  // no se movio: nada que avisar
        // UN SOLO widget se escribe (el relevo), no los dos <input> del
        // slider nativo — ver el docstring de Python de esta función.
        //
        // 'input'/'change' NO ALCANZA para confirmar un `st.text_input`
        // (medido: el valor queda puesto en el DOM, pero Streamlit nunca
        // corre el `on_change` — cero rastro en el log del servidor). El
        // widget de react-aria confirma con blur o con Enter; blur
        // TAMPOCO alcanzó (probablemente porque este input está oculto
        // fuera de pantalla, `focusout` en un elemento así no dispara la
        // misma cadena que en uno visible). Un Enter de teclado de
        // verdad —focus, valor, keydown+keyup— SÍ confirma: es el mismo
        // camino que un usuario tecleando y presionando Enter.
        relevo.focus();
        setterInput.call(relevo, nv1 + ',' + nv2);
        relevo.dispatchEvent(new Event('input', {{bubbles: true}}));
        var opts = {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                    bubbles: true, cancelable: true}};
        relevo.dispatchEvent(new KeyboardEvent('keydown', opts));
        relevo.dispatchEvent(new KeyboardEvent('keyup', opts));
      }}
      overlay.addEventListener('pointerup', soltar);
      overlay.addEventListener('pointercancel', soltar);
      }} // fin de adjuntar()
    }})();
    </script>""")


def selector_escala(clave, ctx, bandera=None, escalas=ESCALAS,
                    default="Días"):
    """Escala de tiempo estilo tabla dinámica: granularidad + riel de rango.

    Escribe la MISMA clave canónica que la píldora de fecha de la franja
    (`ctx["k_rango"]`, vía `aplicar_atajo`), así que no es un filtro paralelo
    — es otra forma de tocar el de siempre. `ctx` es el dict de
    `franja_fecha.contexto()`.

    DOS WIDGETS SEGÚN LA ESCALA, y no es capricho:
      · "Días" → `st.slider` de fechas. Continuo, y las flechas del teclado
        mueven un día exacto. Un riel discreto de ~970 paradas en 250px da
        4 días por píxel: se ve lindo y no se puede elegir una fecha.
      · "Meses"/"Años" → `st.select_slider` sobre `escala_periodos()`. Son
        pocas paradas y cada una tiene que caer donde empieza el período.

    LA CLAVE ES POR ESCALA (`{clave}_dias`, `_meses`, `_anos`). Compartir
    una sola reventaría: el valor guardado en Días es un `date` cualquiera y
    en Meses tiene que ser un arranque de mes de `options`, y un
    `select_slider` cuyo estado no está en `options` tira excepción. De yapa,
    volver a una escala recupera lo que tenía. Los sufijos salen de
    `_slug_url` (ASCII): "Días"/"Años" con tilde en una key emiten una clase
    CSS distinta de la que uno escribe.

    SIEMBRA: el par se recalcula del rango canónico en cada render, y el
    rango va DENTRO de la key del riel. Así, cuando cambia por afuera (la
    píldora de la franja, un atajo de al lado), el widget es otro y nace
    con `value=` en su lugar. Ver el comentario largo más abajo: borrar la
    clave de `session_state` —el camino obvio— no alcanza.
    """
    if not ctx:
        return None
    bounds = (ctx.get("fecha_min"), ctx.get("fecha_max"))
    if not all(bounds) or bounds[0] >= bounds[1]:
        return None

    # LA GRANULARIDAD SE ESPEJA EN UNA CLAVE QUE NO ES DE WIDGET, y esto
    # NO es paranoia — sin el espejo el control vuelve solo a "Días" cada
    # vez que se mueve un tirador (medido 2026-08-25: el DOM mostraba
    # "Meses" marcado y Python dibujaba el riel de `_dias`).
    #
    # La cadena: mover el tirador dispara el callback → Streamlit re-corre
    # el FRAGMENT → el fragment aborta en su primera línea con
    # `st.rerun(scope="app")` (la escalada que necesita el filtro, que vive
    # fuera) → en ese run ningún widget del popover llegó a dibujarse → y
    # un widget que no se dibuja pierde su estado. En el rerun completo el
    # `segmented_control` nace de cero y toma `default`.
    #
    # Es la regla de CLAUDE.md ("un widget que deja de renderizarse pierde
    # su estado") en un caso que no se ve venir: acá no se esconde nada, lo
    # esconde un `rerun` que corta el run por la mitad. Los cuatro atajos
    # de al lado convivían con esto sin síntoma porque un `st.button` no
    # guarda nada.
    #
    # El espejo es una clave normal de session_state: nadie la recolecta.
    # De yapa arregla el des-seleccionar (el `segmented_control` devuelve
    # `None` y antes eso caía al default en vez de quedarse donde estaba).
    k_eco = f"{clave}__gran_eco"
    previo = st.session_state.get(k_eco, default)
    if previo not in escalas:
        previo = default
    escala = st.segmented_control(
        "Escala", list(escalas), default=previo,
        key=f"{clave}_gran", label_visibility="collapsed") or previo
    st.session_state[k_eco] = escala

    rango = st.session_state.get(ctx["k_rango"])
    ventana = None
    if escala == "Días":
        # EL RIEL ABARCA UN MES, no el histórico entero (a pedido
        # 2026-08-26, con la captura del selector de Excel: "cuando
        # selecciono Días sólo necesitaría ver la línea del mes en curso,
        # no debo ver el año 2023"). El ancla es el FIN del rango vigente
        # —"el mes en curso"—; sin rango, el último día con datos.
        _ancla = (max(rango) if rango and len(rango) == 2 and all(rango)
                  else bounds[1])
        ventana = ventana_mes(_ancla, bounds)
        if not ventana:
            return escala
        par = ((min(rango), max(rango))
               if rango and len(rango) == 2 and all(rango) else ventana)
        # Se recorta a la VENTANA, no a `bounds`. Un rango que se pasa del
        # mes (venir de "últimos 12 meses" y cambiar a Días) se DIBUJA
        # apoyado en el borde, pero no se reescribe: el riel sólo escribe
        # cuando el usuario mueve algo, misma doctrina que el redondeo
        # hacia afuera de `escala_desde_rango`. El caption de abajo canta
        # la diferencia para que el control no mienta.
        par = (min(max(par[0], ventana[0]), ventana[1]),
               min(max(par[1], ventana[0]), ventana[1]))
    else:
        # MISMA IDEA QUE DÍAS, un piso más arriba cada vez: Meses mira un
        # año, Años una década (`_VENTANA_DE_ESCALA`). El riel de Meses
        # abría con los ~44 meses del histórico en 250px.
        _ancla = (max(rango) if rango and len(rango) == 2 and all(rango)
                  else bounds[1])
        _fn_ventana = _VENTANA_DE_ESCALA.get(escala)
        ventana = _fn_ventana(_ancla, bounds) if _fn_ventana else None
        if _fn_ventana and not ventana:
            return escala
        # `escala_desde_rango` recibe la VENTANA como bounds, no el
        # histórico: así sus paradas son las de ese período y el redondeo
        # hacia afuera apoya en el borde lo que se sale — que es justo lo
        # que ya hacía contra el histórico, un nivel más abajo. El `or
        # bounds` cubre una escala futura que decida no llevar ventana.
        par = escala_desde_rango(escala, rango, ventana or bounds)
        if not par:
            return escala

    # LA KEY CODIFICA EL RANGO, y esto merece explicación porque a primera
    # vista contradice a CLAUDE.md ("sin key dinámica").
    #
    # El primer intento fue el que manda la regla: key fija, y borrar la
    # clave de `session_state` cuando el rango cambiaba por afuera para que
    # el widget renaciera con `value=`. NO FUNCIONA, y falla en silencio:
    # borrar la clave del lado del servidor no le borra nada al NAVEGADOR,
    # que sigue mandando el valor viejo de ese widget en el mensaje
    # siguiente y Streamlit lo re-aplica. Medido 2026-08-25: se apretaba
    # "Este año", la píldora de la franja pasaba a "1 ene – 21 ago" y el
    # caption a "233 días" —o sea, ESTA función ya corría con el rango
    # nuevo— y el riel seguía marcando "jul 26 | ago 26".
    #
    # Con el rango en la key, un cambio externo produce un widget DISTINTO
    # y el navegador no tiene valor viejo que mandar. Y el espíritu de la
    # regla se respeta igual: lo que prohíbe es que el widget sea el DUEÑO
    # del dato y se desincronice del display. Acá el dueño es la clave
    # canónica del rango, siempre; el riel es una VISTA que se recalcula de
    # ella en cada render. Por eso también desapareció la firma: la key ES
    # la firma.
    k_riel = (f"{clave}_{_slug_url(escala)}"
              f"_{par[0]:%Y%m%d}_{par[1]:%Y%m%d}")
    if ventana:
        # La VENTANA también entra en la firma: define los límites del riel
        # (`min_value`/`max_value` en Días, `options` en Meses), y un widget
        # con la misma key y otros límites se queda con el valor viejo que
        # le manda el NAVEGADOR — el mismo fallo que explica el comentario
        # de arriba, con otra cara.
        k_riel += f"_v{ventana[0]:%Y%m%d}{ventana[1]:%Y%m%d}"

    if escala == "Días":
        _nav_ventana(clave, escala, ventana, bounds, ctx, bandera)
        st.slider("Rango", min_value=ventana[0], max_value=ventana[1],
                  value=par, key=k_riel, format="DD/MM/YY",
                  label_visibility="collapsed",
                  on_change=_aplicar_escala,
                  args=(k_riel, escala, ctx, bandera))
        # 2026-08-26, a pedido ("la línea no tiene ninguna indicación de
        # qué día o mes estoy seleccionando"): el `st.slider` nativo sólo
        # dibuja los DOS extremos del rango completo como referencia (medido
        # en el DOM: `stSliderTickBar` trae nada más que min y max) — nada
        # entre medio dice si el tirador está pasando por 2024 o por 2026.
        # Se agrega una regla de años DEBAJO, no ENCIMA del riel: overlayarla
        # sobre el track de Streamlit exigiría calzar a mano su alto interno
        # (frágil — cambia con la versión de Streamlit); una fila propia,
        # del mismo ancho, es la misma info sin tocar el DOM ajeno.
        # El mapeo es 0%–100% lineal sobre `bounds`, verificado en vivo: la
        # posición `left%` que Streamlit le da a cada tirador coincide
        # exactamente con `(valor - min) / (max - min)` sin ningún inset por
        # el radio del círculo — así que la MISMA cuenta sirve acá.
        _total_dias = (ventana[1] - ventana[0]).days
        if _total_dias > 0:
            # Regla de DÍAS DEL MES. Hasta esta misma fecha era de AÑOS,
            # porque el riel abarcaba todo el histórico; con la ventana de
            # un mes, los años sobran y lo que falta es el número de día
            # —que es justo lo que rotula Excel debajo de su franja—.
            # Uno cada 5 más los dos bordes, y no los 31 como Excel, porque
            # su franja es mucho más ancha: 31 etiquetas en ~250px son 8px
            # por día y dos dígitos no entran. Las paradas de 5 que caen
            # pegadas a un borde se saltean, o se pisan con él.
            _marcas = sorted({ventana[0], ventana[1]} | {
                _d for _d in escala_periodos("Días", ventana)
                if _d.day % 5 == 0
                and (_d - ventana[0]).days >= 2
                and (ventana[1] - _d).days >= 2})
            _spans = "".join(
                f'<span style="left:{(_m - ventana[0]).days / _total_dias * 100:.2f}%">'
                f'{_m.day}</span>'
                for _m in _marcas)
            st.markdown(f'<div class="cp-riel-regla">{_spans}</div>',
                       unsafe_allow_html=True)
            # Relevo oculto para "arrastrar la línea entera" (a pedido,
            # "como el slider de Excel") — ver el docstring largo de
            # `_aplicar_pan_riel` para por qué es un widget propio y no
            # los dos `<input>` nativos del slider.
            _k_relevo = f"{k_riel}_pan"
            st.text_input("pan", key=_k_relevo, label_visibility="collapsed",
                          on_change=_aplicar_pan_riel,
                          args=(_k_relevo, ctx, bandera))
            _arrastrar_ventana_riel(k_riel, _k_relevo, ventana)
    else:
        if ventana:
            _nav_ventana(clave, escala, ventana, bounds, ctx, bandera)
        st.select_slider("Rango",
                         options=escala_periodos(escala, ventana or bounds),
                         value=par, key=k_riel,
                         format_func=lambda d: _fmt_periodo(escala, d),
                         label_visibility="collapsed",
                         on_change=_aplicar_escala,
                         args=(k_riel, escala, ctx, bandera))

    # El slider ya dibuja sus dos extremos; repetir las fechas sería ruido.
    # Lo que NO dice es cuánto abarca, que es el dato con el que se decide
    # si el rango alcanza para lo que uno quiere mirar.
    if rango and len(rango) == 2 and all(rango):
        _n = abs((max(rango) - min(rango)).days) + 1
        _txt = (f"{_n} días seleccionados" if _n != 1
                else "1 día seleccionado")
        # Y si el rango vigente SE SALE del mes visible, decirlo. El riel
        # lo dibuja apoyado en el borde (ver el recorte de `par` arriba);
        # sin esta línea el control mostraría "1–24 ago" mientras la tabla
        # filtra doce meses, que es exactamente la desincronización que
        # `estado_rango` existe para evitar.
        if ventana and (min(rango) < ventana[0] or max(rango) > ventana[1]):
            _txt += (f" · el riel muestra sólo "
                     f"{_rotulo_ventana(escala, ventana).lower()}")
        st.caption(_txt)
    return escala


def _render_rail(categorias, state_key, btn_prefix="graf_btn_",
                 secciones=None):
    """Vistas del reporte activo — fila de TABS DE TEXTO en la franja
    superior. Selector de tipo de gráfico/pantalla dentro de un reporte.

    Componente COMPARTIDO: es el layout estándar de los dashboards (Compras,
    Ajuste, …). Dibuja dentro de `st.container(key="nav_rail")` — la MISMA
    key que usa `navegacion.py::inject_navegacion` para la franja de
    Reportes: son dos contenidos que ocupan la franja superior en dos
    momentos DISTINTOS del script (Reportes se resuelve antes del
    `@st.fragment` de `_render_contenido`, Vistas adentro — ver el docstring
    de `inject_navegacion`), nunca simultáneos, así que compartir la key no
    los pisa. Ver arquitectura.md regla #170 (inversión Reportes↔Vistas).

    Hasta el 2026-08-22 este rail era VERTICAL, a la izquierda, con
    categorías agrupadas por badge (`rail-cat-badge`) — ese lugar y ese
    formato los ocupa ahora Reportes (`compras_tabs_row`, ver
    `inject_navegacion`). Acá las categorías se APLANAN a una sola fila de
    texto: una franja horizontal no tiene el alto para mostrar grupos, mismo
    criterio que ya se aplicó a Reportes cuando bajó de rail a franja el
    2026-08-18.

    Parámetros
      · categorias: `((nombre_categoria, ((id, label[, icono]), …)), …)`.
        El nombre de categoría no se dibuja — se ignora a propósito, ver
        arriba. Se mantiene la MISMA forma de parámetro que antes del swap
        para no tocar los 9 call sites; son los dashboards los que siguen
        agrupando sus vistas por categoría en el código, aunque visualmente
        ya no se note.

        El ícono (3er elemento opcional) lo dibuja SOLO la copia vertical
        de la columna izquierda, que tiene alto para él; la franja
        horizontal lo sigue ignorando por el mismo motivo de siempre.
      · state_key: clave de session_state donde se persiste la selección.
      · btn_prefix: prefijo de las keys de los botones (único por reporte si dos
        rails pudieran coexistir; hoy solo hay un reporte activo por vez).

    Devuelve el id de la opción seleccionada (persistida en session_state, así
    sobrevive al rerun del clic sin doble render).
    """
    _todos = [item[0] for _, items in categorias for item in items]
    if not _todos:
        return None
    # ── Deep-link: el item del rail viaja en ?vista= ─────────────────────
    # Sin esto, la URL sólo decía el reporte y llegar a una pantalla
    # concreta eran 3-5 clics encadenados, cada uno con su rerun. Además
    # no se podía compartir "mirá ESTA pantalla": había que describirla.
    # Va acá, en el rail COMPARTIDO, así vale para los 9 dashboards de una.
    sel = st.session_state.get(state_key)
    if sel not in _todos:
        # Todavía no hay selección válida: primera carga, o venimos de otro
        # reporte cuyo rail tenía otros ids. Ahí manda la URL, si trae uno
        # que exista en ESTE rail; si no, el primer item de siempre.
        # El match va por `_norm` (ignora acentos Y separadores), así entra
        # igual "comparativo_vs_ano_pasado" que "Comparativo vs Año Pasado".
        sel = vista_activa(categorias, state_key)
        st.session_state[state_key] = sel
    # SIN wrapper interno propio (a diferencia del rail vertical, que abre
    # `graf_tipo_chips` adentro): los botones van DIRECTOS dentro de
    # `nav_rail`, igual que dibujaba Reportes antes del 2026-08-22.
    #
    # OJO con el corolario, que costó un bug (arquitectura.md regla #201):
    # sacar el wrapper NO hace que el CSS viejo "se reuse solo". El
    # contenedor de `st.container(key="nav_rail")` ES el stVerticalBlock que
    # lleva la key, así que un selector DESCENDIENTE
    # (`.st-key-nav_rail [data-testid="stVerticalBlock"]`) pasó de matchear
    # el wrapper a no matchear nada — en silencio, porque el rail seguía
    # viéndose como una fila gracias a las reglas del propio `.st-key-nav_rail`.
    # Lo que se perdió fue el `gap:0`, y con él volvió el `gap:1rem` de
    # Streamlit: 112px de más que sacaban "Tabla" de pantalla a 900px.
    # Si agregás una regla para esta fila, colgala del RAIL, no de un hijo.
    st.markdown(_CSS_FRANJA_VISTAS, unsafe_allow_html=True)
    with st.container(key="nav_rail"):
        for _cat_nombre, items in categorias:
            for item in items:
                oid, label = item[0], item[1]
                st.button(
                    label,
                    key=f"{btn_prefix}{_slug(oid)}",
                    type=("primary" if oid == sel else "secondary"),
                    on_click=_rail_set, args=(state_key, oid),
                )
    # ── Copia VERTICAL del rail, para la columna izquierda ───────────────
    # Solo se dibuja si el dashboard declara `secciones`, o sea si su página
    # es una PILA que se lee bajando. Hoy la tiene Compras; los otros 8
    # dashboards no pasan nada y no pagan nada: ni rail extra, ni iframe.
    #
    # `secciones` es `((clave_contenedor, id_vista), ...)` EN EL ORDEN de la
    # página. El id de vista es el mismo que el del rail, así que el slug del
    # botón se calcula acá y el dashboard no tiene que adivinarlo.
    #
    # Qué hace el rail acá: deja de ELEGIR contenido (está todo dibujado) y
    # pasa a ser NAVEGACIÓN — marca en qué sección estás y te lleva a la que
    # toques. Las dos mitades son de JS y ninguna dispara un rerun:
    #
    #   · el resaltado sale de una clase que pone el scrollspy, no de
    #     `type="primary"`, porque seguir el scroll desde Python costaría un
    #     rerun por cada pixel. Por eso los botones van todos `secondary`:
    #     si además se pintara el elegido habría dos marcas discutiendo —
    #     la de dónde estás y la del último clic;
    #   · el clic scrollea y corta el evento antes de que Streamlit lo vea.
    #     Sin eso el botón reconstruía la página entera (~45s) para dejarte
    #     donde ya estabas: es lo que pasaba y se reportó como bug — bajabas
    #     hasta Tabla, tocabas otra vista y no te movías de sitio.
    #
    # Por qué una segunda copia del rail y no mover la franja horizontal: su
    # `top/left/width` están fijados con `!important` en
    # `navegacion.py::_CSS_FRANJA_VISTAS`, y en la cascada el origen de
    # ANIMACIÓN va por DEBAJO de las declaraciones `!important` del autor.
    # Ver arquitectura.md regla #200.
    if secciones:
        # El gemelo del rótulo de Reportes (`navegacion.py`): esta columna
        # reemplaza a aquella al bajar, así que el rótulo también se cambia.
        # Sin esto la tarjeta cambia de contenido bajo un rótulo que sigue
        # diciendo "Reportes", que es justo lo que el rótulo viene a evitar.
        with st.container(key="rail_rotulo_vis"):
            st.markdown('<div class="rail-rotulo">Vistas</div>',
                        unsafe_allow_html=True)

        with st.container(key="nav_rail_lateral"):
            # ── Cabecera: DÓNDE ESTÁS ────────────────────────────────────
            # Esta columna reemplaza a la lista de Reportes al bajar, y con
            # ella se iba el nombre del reporte que estás leyendo. La
            # cabecera lo devuelve, con sus mismos KPIs — el patrón de las
            # fichas de MSN Dinero, que encabezan su rail con la entidad
            # (nombre + cotización) y debajo listan sus secciones.
            #
            # `navegacion.py` ya la dejó calculada y formateada: acá sólo se
            # pinta. Ver `CLAVE_CABECERA`.
            _cab = st.session_state.get(navegacion.CLAVE_CABECERA)
            if _cab and _cab.get("nombre"):
                _kpi = ""
                if _cab.get("primario"):
                    _cls = ("rail-cab-kpi kpi-neg" if _cab.get("negativo")
                            else "rail-cab-kpi")
                    _kpi = f'<span class="{_cls}">{html.escape(_cab["primario"])}</span>'
                    if _cab.get("secundario"):
                        _kpi += ('<span class="rail-cab-kpi2">'
                                 f'{html.escape(_cab["secundario"])}</span>')
                st.markdown(
                    '<div class="rail-cab">'
                    f'<div class="rail-cab-nom">{html.escape(_cab["nombre"])}</div>'
                    f'{_kpi}'
                    '</div>',
                    unsafe_allow_html=True,
                )

            # 2026-08-26, a pedido ("el reporte de documentos sunat no
            # aparece al hacer scroll"): no era un bug de clic —
            # verificado en el navegador, clickear "Documentos" SÍ
            # cambia de pantalla, correcto— sino de EXPECTATIVA. El
            # rail lista sus 7 ítems seguidos, sin distinguir cuáles son
            # scroll-to (los 6 de `_PILA`) de cuál es un DESTINO APARTE
            # (Documentos SUNAT, ver el comentario de `_PILA` más
            # arriba en graficos/compras/__init__.py): entre Volatilidad
            # y Semanal, con la MISMA pinta, nada avisaba que ahí el
            # scroll no lleva a ningún lado.
            #
            # La línea se dibuja en las dos transiciones (entra Y sale
            # del grupo), no solo antes de Documentos: `secciones` es
            # de UN dashboard, y un rail futuro con dos o más destinos
            # aparte intercalados necesita marcar cada frontera, no una
            # posición fija.
            _ids_pila = {_oid for _, _oid in secciones}
            _prev_en_pila = None
            for _cat_nombre, items in categorias:
                for item in items:
                    oid, label = item[0], item[1]
                    _en_pila = oid in _ids_pila
                    if _prev_en_pila is not None and _en_pila != _prev_en_pila:
                        st.markdown('<div class="nav-rail-lat-sep"></div>',
                                   unsafe_allow_html=True)
                    _prev_en_pila = _en_pila
                    # El icono SÍ se dibuja acá (a diferencia de la franja
                    # horizontal, que lo ignora por falta de alto): esta copia
                    # es vertical y tiene sitio. Y hace falta — el rail que
                    # reemplaza, el de Reportes, tiene iconos, y sin ellos el
                    # intercambio se ve como un salto de formato.
                    # 3er elemento opcional: hay rails con tuplas de 2.
                    icono = item[2] if len(item) > 2 else None
                    st.button(
                        label,
                        key=f"{btn_prefix}lat_{_slug_url(oid)}",
                        type="secondary",
                        on_click=_rail_set, args=(state_key, oid),
                        **({"icon": icono} if icono else {}),
                    )

        # ── El rail: marcado + activación ────────────────────────────────
        # Un temporizador que mide geometría, no observers. El porqué de cada
        # decisión está en el propio JS de abajo; en resumen: los umbrales de
        # `IntersectionObserver` no alcanzan para marcar secciones más altas
        # que la pantalla, y las activaciones tienen que ir de a una o
        # Streamlit pierde clics.
        #
        # Va en `inyectar_html` y no en `st.markdown` porque markdown NO
        # ejecuta `<script>` (regla #4); ese primitivo mete un iframe de
        # verdad y reemplaza a `components.html` (regla #204).
        _mapa = [{"sec": _cl, "btn": f"{btn_prefix}lat_{_slug_url(_oid)}",
                   "go": f"pila_go_{_cl}"}
                 for _cl, _oid in secciones]
        with st.container(key="rail_scroll_hook"):
            inyectar_html(
                f"""<script>
                (function () {{
                  var w = window.parent, doc = w.document;
                  var MAPA = {json.dumps(_mapa, ensure_ascii=False)};
                  var raiz = doc.querySelector('[data-testid="stMain"]');
                  if (!raiz) return;

                  // UN SOLO TEMPORIZADOR POR GEOMETRIA, no observers.
                  //
                  // Hace dos cosas: marcar en el rail la seccion que estas
                  // mirando, y activar la siguiente antes de que llegues.
                  // Las dos se resolvieron igual y por los mismos motivos:
                  //
                  //  · `IntersectionObserver` NO sirve para el marcado. Sus
                  //    callbacks llegan al CRUZAR un umbral, y una seccion
                  //    mas alta que la pantalla no vuelve a cruzar ninguno
                  //    mientras la recorres: el dato queda viejo y el rail
                  //    no cambia. Pasó exactamente eso (2026-08-25).
                  //  · `getBoundingClientRect` es SINCRONO y siempre dice la
                  //    verdad de ahora. Ademas no depende de que el
                  //    navegador entregue callbacks de renderizado.
                  //
                  // La activacion va de a UNA y espera a que el servidor
                  // este libre: clickear varias juntas hace que Streamlit
                  // procese una y pierda las otras (medido: 3 clicks, una
                  // sola seccion construida). Y la condicion de "ya esta" se
                  // lee del DOM, asi que un clic perdido se reintenta solo.
                  if (w.__railTimer) clearInterval(w.__railTimer);
                  w.__railTimer = setInterval(function () {{
                    var caja = raiz.getBoundingClientRect();

                    // ── 1. Marcar la seccion con MAS pixeles a la vista ──
                    var mejor = null, mejorPx = 0;
                    MAPA.forEach(function (m) {{
                      var s = doc.querySelector('[class*="st-key-' + m.sec + '"]');
                      if (!s) return;
                      var r = s.getBoundingClientRect();
                      var vis = Math.min(r.bottom, caja.bottom)
                              - Math.max(r.top, caja.top);
                      if (vis > mejorPx) {{ mejorPx = vis; mejor = m; }}
                    }});
                    if (mejor) {{
                      // El rail de la columna cambia de Reportes a Vistas en
                      // cuanto dejas la primera seccion.
                      doc.documentElement.classList.toggle(
                        'rails-scrolled', mejor.sec !== MAPA[0].sec);
                      var previos = doc.querySelectorAll('.vista-en-pantalla');
                      for (var i = 0; i < previos.length; i++) {{
                        previos[i].classList.remove('vista-en-pantalla');
                      }}
                      var b = doc.querySelector(
                        '[class*="st-key-' + mejor.btn + '"] button');
                      if (b) b.classList.add('vista-en-pantalla');
                    }}

                    // ── 2. Activar la proxima, de a una ─────────────────
                    if (doc.querySelector('[data-testid="stStatusWidget"]')) return;
                    for (var j = 0; j < MAPA.length; j++) {{
                      var m2 = MAPA[j];
                      var s2 = doc.querySelector('[class*="st-key-' + m2.sec + '"]');
                      if (!s2 || !s2.querySelector('.pila-hueco')) continue;
                      if (s2.getBoundingClientRect().top - caja.bottom > 900) continue;
                      var g = doc.querySelector(
                        '[class*="st-key-' + m2.go + '"] button');
                      if (g) {{ g.click(); return; }}
                    }}
                  }}, 400);

                  // El CLIC LLEVA a la seccion. Se intercepta en captura y se
                  // corta ahi: React escucha en la raiz del documento, asi que
                  // detener la propagacion antes evita que Streamlit vea el
                  // clic y dispare un rerun. Sin esto el boton reconstruia la
                  // pagina entera para dejarte donde ya estabas.
                  //
                  // Solo los botones de la PILA. Los que son destino aparte
                  // (Documentos SUNAT) tienen que seguir
                  // haciendo su navegacion normal.
                  MAPA.forEach(function (m) {{
                    var b = doc.querySelector('[class*="st-key-' + m.btn + '"] button');
                    var s = doc.querySelector('[class*="st-key-' + m.sec + '"]');
                    if (!b || !s || b.__railClic) return;
                    b.__railClic = true;
                    b.addEventListener('click', function (ev) {{
                      ev.preventDefault();
                      ev.stopPropagation();
                      var franja = doc.querySelector('[class*="st-key-nav_rail"]');
                      var techo = franja ? franja.getBoundingClientRect().height : 0;
                      var y = s.getBoundingClientRect().top
                            - raiz.getBoundingClientRect().top
                            + raiz.scrollTop - techo - 8;
                      raiz.scrollTo({{ top: Math.max(0, y), behavior: 'smooth' }});
                    }}, true);
                  }});
                }})();
                </script>""",
            )

    _final = st.session_state.get(state_key, _todos[0])
    # Espejo hacia la URL. Escribir query_params NO dispara rerun, pero se
    # compara antes igual: reescribir en cada rerun es ruido inútil.
    if st.query_params.get("vista") != _slug_url(_final):
        st.query_params["vista"] = _slug_url(_final)
    return _final


@contextmanager
def _card(key, titulo: str = "", titulo_arriba: bool = False):
    """Card nativo para un gráfico. `key` debe ser único por rerun.
    Con `titulo`:
      - por defecto se muestra al pie (clase .chart-card-pie);
      - si `titulo_arriba=True`, se muestra como cabecera arriba del card,
        con divisoria (clase .chart-card-hdr, estilizada en estilos.py)."""
    with st.container(border=True, key=f"chartcard_{_slug(key)}"):
        if titulo and titulo_arriba:
            st.markdown(
                f'<p class="chart-card-hdr">{titulo}</p>',
                unsafe_allow_html=True,
            )
        yield
        if titulo and not titulo_arriba:
            st.markdown(
                f'<p class="chart-card-pie">{titulo}</p>',
                unsafe_allow_html=True,
            )


def publicar_var_px(nombre, px):
    """Publica un número de píxeles calculado en Python como VARIABLE CSS,
    para que las restas y las derivaciones las haga el navegador.

    Nació para los altos (ver `alturas.py` § LA RESTA NO SE HACE ACÁ) y hoy
    lo usan también los anchos de los rails plegables:
    el alto de una figura sólo lo puede decidir Python —Plotly ignora su
    contenedor—, pero el alto DISPONIBLE sólo lo conoce el navegador
    (`100dvh`). Cuando Python hace las dos cosas, resta contra una pantalla
    supuesta (`alturas.VIEWPORT_OBJETIVO`) y el resultado es correcto en un
    solo monitor. Publicando el número, el CSS puede escribir la resta
    verdadera:

        publicar_var_px("vh-alto-arriba", 351)
        /* en estilos/: */
        max-height: calc(var(--alto-util) - var(--vh-alto-arriba));

    SIN guard de "inyectar una sola vez": un `st.markdown` de estilos
    desaparece en el rerun siguiente (arquitectura.md regla #59), así que
    esto tiene que correr en cada render — que además es lo correcto, porque
    el número cambia con los datos.
    """
    st.markdown(
        f"<style>:root{{--{nombre}: {int(px)}px;}}</style>",
        unsafe_allow_html=True,
    )


def franja_cabecera(ph, titulo, color_texto=None):
    """Cabecera de una FRANJA DE CONTROLES: título + línea SUPERIOR que la
    cierra por arriba. Patrón `título → línea → tabs → línea → contenido`
    (arquitectura.md reglas #104/#107), nacido en Ventas › Por día y Año
    Pasado — este helper es la 3ª implementación, para no dejar una tercera
    copia con valores a mano que drifteen entre sí (las dos primeras YA
    tienen -15px/-18px/14px vs -6px/-18px/12px en el `<hr>` de abajo:
    exactamente el drift que este helper existe para frenar).

    `ph` es el `st.empty()` (o el propio `st`/contenedor) donde se pinta —
    normalmente un placeholder para poder escribir el título DESPUÉS de leer
    los controles que van debajo de él (ver `franja_linea_inferior` y el
    patrón de `session_state` en ventas_comparativo.py, regla #108: si el
    título depende de un widget que vive dentro de la misma franja, pintarlo
    dos veces —provisional con `session_state`, final con el valor real— es
    lo que evita el "salto" de layout en cada clic)."""
    color = color_texto or TEXTO_PRINCIPAL
    ph.markdown(
        '<div style="margin:-6px -18px 0;padding:0 18px 9px;'
        'width:calc(100% + 36px);font-size:16px;font-weight:600;'
        f'line-height:1.3;color:{color};'
        f'border-bottom:2px solid {GRIS_BORDE};">{titulo}</div>',
        unsafe_allow_html=True)


def titulo_en_franja(ph, titulo):
    """Pinta `titulo` en un placeholder que vive FUERA de la tarjeta y se
    ancla a la franja superior por CSS (position:fixed, con key propia por
    vista — ver estilos/_50_fecha.py, sección por dashboard). El `title=`
    del span es el tooltip para cuando el ellipsis del CSS lo trunca.

    Nace en Ventas › Comparativo (arquitectura.md regla #120) y se reusa en
    Compras › Familia para que una 3ra copia a mano no vuelva a driftear —
    mismo motivo por el que existe `franja_cabecera` más arriba."""
    ph.markdown(f'<span title="{titulo}">{titulo}</span>',
                unsafe_allow_html=True)


def franja_linea_inferior():
    """Línea INFERIOR que cierra una franja de controles por abajo, tocando
    el borde REAL de la tarjeta. Los -18px + `width:calc(100% + 36px)`
    compensan el padding horizontal de la tarjeta (16px 18px,
    `estilos/_80_cards.py`); sin eso la línea queda corta por los dos
    lados. Hermana de `franja_cabecera` — ver su docstring."""
    st.markdown(
        f'<hr style="border:none;border-top:2px solid {GRIS_BORDE};'
        'margin:-6px -18px 12px;width:calc(100% + 36px);">',
        unsafe_allow_html=True)


_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=BLANCO,
    font_color=TEXTO_PRINCIPAL,
    font_family="DM Sans, Inter, -apple-system, sans-serif",
    margin=dict(l=20, r=20, t=50, b=20),
    # El alto NO se escribe suelto: sale de graficos/alturas.py, que es su
    # único dueño (ver su docstring: en este stack Plotly sólo obedece a
    # fig.layout.height, así que el número tiene que salir de Python).
    # APOYO vale 380, exactamente lo que este default decía antes.
    height=alturas.APOYO,
    barcornerradius=6,          # ← NUEVO: esquinas redondeadas en TODAS las barras
    xaxis=dict(gridcolor=GRIS_BORDE),
    yaxis=dict(gridcolor=GRIS_BORDE, tickformat=",.0f"),
)


def _layout(**overrides):
    """_LAYOUT_BASE fusionado con `overrides`, aplicando a los ejes de
    TODOS los gráficos un estilo común:
      · sin valores en el eje Y (la cuadrícula interna SÍ se ve)
      · nombres del eje X horizontales (tickangle=0 + automargin)

    La cuadrícula conserva su color; solo se ocultan las ETIQUETAS del
    eje Y y se enderezan los nombres del eje X. Los overrides del gráfico
    se respetan y luego se les inyecta este estilo encima.

    Los gráficos cuyo eje Y lleva nombres (no valores numéricos) — p. ej.
    el mapa de calor, con familias en Y — pueden pasar showticklabels=True
    en su yaxis para conservar esas etiquetas."""
    base = dict(_LAYOUT_BASE)
    base.update(overrides)

    xaxis = dict(base.get("xaxis", {}))
    yaxis = dict(base.get("yaxis", {}))

    xaxis.update(tickangle=0, automargin=True,
                 showline=False, zeroline=False, mirror=False)
    yaxis.update(showline=False, zeroline=False, mirror=False)
    yaxis.setdefault("showticklabels", False)  # oculta valores del eje Y

    base["xaxis"] = xaxis
    base["yaxis"] = yaxis
    return base


def _wrap_cat(labels, width=14):
    """Parte etiquetas de categoría largas en varias líneas (con <br>) para
    que, mostradas en horizontal, no se enciman. `width` es el número
    aproximado de caracteres por línea. Se usa como `ticktext` del eje X,
    así que el hover (que lee el valor real) no se ve afectado."""
    out = []
    for lab in labels:
        s = str(lab)
        if len(s) <= width:
            out.append(s)
            continue
        lineas, actual = [], ""
        for palabra in s.split():
            if actual and len(actual) + 1 + len(palabra) > width:
                lineas.append(actual)
                actual = palabra
            else:
                actual = palabra if not actual else f"{actual} {palabra}"
        if actual:
            lineas.append(actual)
        out.append("<br>".join(lineas))
    return out


def paso_etiquetas(total_columnas, largo_etiqueta, ancho, px_fuente=10):
    """Cada cuántas columnas se escribe una etiqueta en el eje X.

    Gemela horizontal de `alturas.por_filas`: ahí el alto sale de los px por
    fila, acá la densidad de etiquetas sale de los px por etiqueta. Vive en
    `base` y no en un dashboard porque la usan dos paquetes distintos
    (`ventas_horario` y `compras/proveedor`) — hasta 2026-08-22 había TRES
    copias del mismo cálculo, y la única con la fórmula buena era privada de
    `ventas_horario`.

    CUENTA PRIMERO CUÁNTAS ENTRAN (`ancho // px_etiqueta`) y recién después
    cada cuántas hay que saltar. El orden importa: calcular el paso directo
    con `ceil(total * px_etiqueta / ancho)` —como se hacía antes— redondea
    DOS veces (una acá y otra en el `ceil(total / paso)` implícito al
    filtrar), y el sobrante se va siempre para el lado de dibujar etiquetas
    de MÁS. A 770px de ancho el error queda diluido y no se nota; a 206px
    daba 5 etiquetas donde entran 4.4 y las cuatro parejas se pisaban entre
    -1 y -5px (medido en Compras › Proveedor, ver arquitectura.md #161).

    `px_fuente` es el tamaño del tick. El ancho de un carácter va a ~0.5 de
    la fuente: medido, "ago 25" (6 caracteres) ocupa 41px con la fuente en
    13px, o sea 6.8 por carácter. Más 8px de aire entre etiqueta y etiqueta.
    El default de 10 conserva la calibración original (5px por carácter).

    `ancho` es OBLIGATORIO a propósito: era un default de módulo
    (`_ANCHO_UTIL`) y por eso nadie notó que el gráfico de Proveedor había
    pasado de ~380px a 206 al partirse su columna en dos. Que cada llamador
    tenga que escribir su ancho lo obliga a mirarlo.
    """
    ancho = max(1, int(ancho))
    px_etiqueta = 8 + max(1.0, 0.5 * px_fuente) * max(1, int(largo_etiqueta))
    total = max(1, int(total_columnas))
    caben = max(1, int(ancho // px_etiqueta))
    return max(1, -(-total // caben))          # ceil(total / caben)


def _resolver(df, candidatos):
    """Resuelve una lista de candidatos (o un string) a la columna real."""
    if candidatos is None:
        return None
    if isinstance(candidatos, str):
        candidatos = [candidatos]
    return buscar_columna(df, *candidatos)


def _preparar_datos(df, x, y, color, tipo):
    """Agrupa los datos según el tipo de gráfico. Si x es fecha, agrupa por mes."""
    if pd.api.types.is_datetime64_any_dtype(df[x]):
        df = df.copy()
        df["_mes"] = df[x].dt.to_period("M").astype(str)
        x = "_mes"

    if tipo in ("bar", "line", "area") and y:
        grupo = [x] + ([color] if color else [])
        df = df.groupby(grupo, as_index=False)[y].sum()

    return df, x


def _hover_fmt(col_y):
    """Devuelve (prefijo, formato_numero) para el valor Y del tooltip."""
    n = _norm(col_y) if col_y else ""
    if any(k in n for k in ("valorizado", "precio", "importe", "total",
                            "monto", "costo", "unitario")):
        return "S/ ", ",.2f"
    if any(k in n for k in ("stock", "cantidad", "qty", "unidades")):
        return "", ",.0f"
    return "", ",.2f"


def crear_grafico(df, conf):
    """Crea una figura Plotly desde una configuración.
    Retorna (fig, None) o (None, motivo) si falta alguna columna."""
    tipo = conf.get("tipo", "bar")

    x = _resolver(df, conf.get("x"))
    y = _resolver(df, conf.get("y"))
    color = _resolver(df, conf.get("color"))
    size = _resolver(df, conf.get("size"))

    if conf.get("x") and not x:
        return None, f"columna X no encontrada ({conf['x']})"
    if conf.get("y") and not y:
        return None, f"columna Y no encontrada ({conf['y']})"

    titulo = conf.get("titulo", f"{y} por {x}")

    try:
        if tipo == "treemap":
            path = [_resolver(df, c) for c in conf.get("path", [])]
            path = [p for p in path if p]
            if not path or not y:
                return None, "faltan columnas para el treemap"
            df_agg = df.groupby(path, as_index=False)[y].sum()
            fig = px.treemap(df_agg, path=path, values=y,
                             color=y, color_continuous_scale=ESCALA_CONTINUA, title=titulo)

        elif tipo == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, size=size, title=titulo)

        elif tipo == "histogram":
            fig = px.histogram(df, x=x, nbins=conf.get("nbins", 20), title=titulo,
                               color_discrete_sequence=[SERIE_PRINCIPAL])

        elif tipo == "box":
            fig = px.box(df, x=x, y=y, color=x if x else None, title=titulo)

        else:  # bar, line, area
            df_p, x_p = _preparar_datos(df, x, y, color, tipo)
            fn = {"bar": px.bar, "line": px.line, "area": px.area}[tipo]
            kwargs = dict(x=x_p, y=y, color=color, title=titulo)
            if tipo == "bar":
                kwargs["barmode"] = conf.get("barmode", "group" if color else "relative")
                kwargs["color_discrete_sequence"] = None if color else [SERIE_PRINCIPAL]
            if tipo == "line":
                kwargs["markers"] = True
            fig = fn(df_p, **kwargs)

        fig.update_layout(**_layout())
        if conf.get("tickangle"):
            fig.update_layout(xaxis_tickangle=conf["tickangle"])

        if tipo in ("bar", "line", "area") and y:
            _pref, _num = _hover_fmt(y)
            fig.update_traces(
                hovertemplate=f"<b>%{{x}}</b><br>{y}: {_pref}%{{y:{_num}}}<extra></extra>"
            )
            fig.update_layout(hovermode="x unified")

        if conf.get("x_categorico"):
            fig.update_xaxes(type="category")

        if conf.get("etiquetas"):
            if tipo == "bar":
                fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
            elif tipo in ("line", "area"):
                fig.update_traces(mode="lines+markers+text",
                                  texttemplate="%{y:,.0f}",
                                  textposition="top center")

        return fig, None

    except Exception as e:
        return None, str(e)


def renderizar_graficos_genericos(df_data, nombre_reporte):
    """Explorador dinámico estilo tabla dinámica."""
    cols_num = df_data.select_dtypes("number").columns.tolist()
    cols_txt = df_data.select_dtypes(["object", "string"]).columns.tolist()
    cols_fecha = [c for c in df_data.columns
                  if pd.api.types.is_datetime64_any_dtype(df_data[c])]

    opciones_x = cols_fecha + cols_txt
    if not cols_num or not opciones_x:
        st.info("No hay suficientes columnas para generar gráficos.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        eje_x = st.selectbox(
            "📅 Eje X", opciones_x,
            format_func=lambda c: f"{c} (por mes)" if c in cols_fecha else c,
            key=f"ejex_{nombre_reporte}",
        )
    with c2:
        eje_y = st.selectbox("📊 Métrica (suma)", cols_num,
                             key=f"ejey_{nombre_reporte}")
    with c3:
        ops_color = ["(ninguna)"] + [c for c in cols_txt if c != eje_x]
        color_sel = st.selectbox("🎨 Serie (color)", ops_color,
                                 key=f"color_{nombre_reporte}")
    with c4:
        tipo_sel = st.selectbox(
            "📈 Tipo", ["Barras", "Barras apiladas", "Líneas", "Área"],
            key=f"tipo_{nombre_reporte}",
        )

    etiquetas = st.toggle("🏷️ Etiquetas de datos", key=f"etq_{nombre_reporte}")

    color = None if color_sel == "(ninguna)" else color_sel
    tipo_map = {"Barras": "bar", "Barras apiladas": "bar",
                "Líneas": "line", "Área": "area"}

    df_plot = df_data
    if eje_x in cols_txt:
        top_cats = (df_data.groupby(eje_x)[eje_y].sum()
                           .sort_values(ascending=False).head(20).index)
        df_plot = df_data[df_data[eje_x].isin(top_cats)]

    conf = {
        "tipo": tipo_map[tipo_sel], "x": eje_x, "y": eje_y, "color": color,
        "titulo": f"{eje_y} por {eje_x}" + (f" y {color}" if color else ""),
        "etiquetas": etiquetas,
    }
    if eje_x in cols_txt:
        conf["tickangle"] = -45
        conf["x_categorico"] = True

    if tipo_sel == "Barras apiladas":
        conf["barmode"] = "stack"

    fig, err = crear_grafico(df_plot, conf)
    if fig:
        fig.update_layout(height=alturas.PROTAGONISTA)
        with _card(f"explorador_{nombre_reporte}"):
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No se pudo generar el gráfico: {err}")

# ===========================================================================
# ALIAS RETROCOMPATIBLES
# ===========================================================================

PALETA_CALLAI = PALETA_SERIES  # alias retrocompatible; fuente en tema.py


# ===========================================================================
# HELPERS DE LAYOUT COMPARTIDOS (nombre '_compras_*' es histórico; los usan
# también ventas e inventario. Se mantienen los nombres para
# no romper contratos existentes.)
# ===========================================================================

def _compras_truncar(s, n=26):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _compras_layout(fig, alto=alturas.PROTAGONISTA):
    """Layout común de los dashboards. `alto` espera un ROL de
    graficos/alturas.py (PROTAGONISTA / APOYO / MINI) o el resultado de
    `alturas.por_filas(...)` — no un literal: ver la regla «nunca un alto
    suelto» en el docstring de ese módulo.

    El nombre `_compras_*` es histórico (nació en Compras); hoy lo usan
    también ventas, inventario, salidas y requerimientos.

    Con `alto=alturas.ELASTICO` la figura sale SIN `height`: el alto lo pone
    el CSS del contenedor y Plotly lo lee al montar. Requiere que el llamador
    pase `height="stretch"` a `st.plotly_chart` y que el CSS le dé alto a la
    cadena de contenedores — ver arquitectura.md regla #106."""
    if alto is alturas.ELASTICO:
        # height=None a propósito: mientras `fig.layout.height` esté puesto,
        # gana siempre y el contenedor no pinta nada (regla #102).
        alto = None
        fig.update_layout(autosize=True)
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        colorway=PALETA_CALLAI,
        # `layout.font` no alcanza al tooltip: Plotly le pone SU PROPIO gris
        # por defecto (~rgb(128,132,149), 3.7:1 sobre blanco — no pasa AA)
        # sin importar el color del resto del gráfico. Reportado "no se ve
        # la información de la etiqueta" sobre el hover de compras/proveedor;
        # se fija acá porque lo pisa cualquier gráfico que use este layout.
        hoverlabel=dict(bgcolor=BLANCO, bordercolor=GRIS_BORDE,
                        font=dict(family="DM Sans, sans-serif",
                                  color=TEXTO_PRINCIPAL, size=12)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor=GRIS_BORDE, zeroline=False)
    return fig
