"""
Navegación de la app: BARRA HORIZONTAL SUPERIOR de reportes, solo texto.

Implementación con BOTONES NATIVOS de Streamlit (sin iframes ni manipulación
del DOM): el click lo maneja Streamlit directamente vía on_click, por lo que
cambiar de reporte es fiable en cada pulsación (no se cuelga ni "deja de hacer
caso"). app.py lee la selección desde st.session_state["_nav_reporte"].

2026-08-18 — DE RAIL LATERAL A FRANJA SUPERIOR
----------------------------------------------
Hasta hoy esto era una columna fija de 90px a la izquierda, con ícono arriba y
etiqueta debajo, plegable con un pestillo. Pasó a ser una franja de 40px
pegada al borde superior, con los reportes en fila y SOLO TEXTO, a pedido y
con referencia concreta (la barra de MSN Dinero): es la jerarquía que usan
casi todas las webapps de reportes financieros, de arriba hacia abajo.

Lo que cambió de raíz, y por qué toca a media docena de módulos de `estilos/`:

  * Los 90px que el rail reservaba en ANCHO los recuperó el contenido. Todo
    lo que estaba anclado con un `left` medido desde el borde de la ventana
    (fecha, chips, título de Ventas) se corrió 90px a la izquierda.
  * Los 40px de la franja salen ahora del ALTO. Todo lo que estaba pegado al
    borde superior (la banda de fecha/chips, el rail derecho de vistas) se
    corre `var(--nav-top-alto)` hacia abajo, y el contenido arranca 40px más
    abajo (`--cab-offset-contenido`, con su gemelo `_CAB_OFFSET` en
    graficos/alturas.py).
  * Ya no hay pestillo izquierdo: una franja horizontal no compite por el
    ancho de la tarjeta, así que no hay nada que recuperar plegándola.

El ALTO de la franja no se escribe acá: es `--nav-top-alto` en
estilos/_00_base.py, porque media docena de reglas de `estilos/` lo restan.
En móvil esa variable vale 0 y esta misma barra se va abajo (bottom nav).
"""

import re
import streamlit as st
import datetime
from zoneinfo import ZoneInfo
from data import solicitar_refresco, secrets_disponibles, fecha_ultima_actualizacion, limpiar_cache
from tema import (
    ACENTO, ACENTO_TEXTO, LAVANDA_FONDO, GRIS_BORDE, GRIS_TEXTO,
)

ZONA_PERU = ZoneInfo("America/Lima")


# El mapa de iconos Bootstrap -> Material Symbols vivió acá hasta el
# 2026-08-18: los botones de navegación eran ícono + etiqueta apilados. La
# franja superior es SOLO TEXTO (a pedido, referencia MSN Dinero), así que el
# `icono` de data.py ya no lo consume la navegación. Sigue en data.py porque
# es parte de la identidad del reporte, por si algún día lo usa otra vista.


def _slug(s):
    return re.sub(r'[^a-zA-Z0-9]+', '_', s)


def _on_nav_click(nombre):
    """Guarda el reporte elegido. Corre ANTES del script => app.py lo ve desde
    arriba en un solo rerun."""
    st.session_state["_nav_reporte"] = nombre


# ── CSS: convierte el contenedor de botones en la franja fija superior ─────
# El ALTO no se escribe acá — es `--nav-top-alto` en estilos/_00_base.py, que
# es de donde lo restan la franja de fecha/chips y el rail derecho.
#
# NAV_X0: dónde arranca el primer reporte. Alinea la fila con el borde
# izquierdo de la TARJETA, no con el de la ventana: es el padding-left que
# Streamlit le pone al block-container, el mismo número del que salen los
# `left` de los chips (_40_ajuste_franja.py) y de la fecha (_50_fecha.py).
NAV_X0 = 64

# ALTURA DE LA BARRA INFERIOR EN MÓVIL (bottom nav). Si cambias este valor,
# actualiza también los "bottom" del bloque móvil de estilos.py
# (.stApp::after, .st-key-footer_actualizacion, toast/aviso y el
# padding-bottom del block-container), que asumen 60px.
NAV_MOVIL_ALTO = 60

_CSS = f"""
<style>
section[data-testid="stSidebar"] {{ display:none !important; }}

/* Sin rail lateral no hay margen izquierdo que reservar. El aire de ARRIBA
   tampoco se pone acá: lo pone el padding-top del block-container
   (--cab-offset-contenido), que ya cuenta esta franja Y la de fecha/chips.
   Sumar un padding-top propio lo contaría dos veces. */
.stApp {{ margin-left:0 !important; padding-top:0 !important; }}

/* Contenedor del rail -> FRANJA HORIZONTAL fija arriba, de borde a borde.
   Blanca con una línea inferior: es cromo, no una tarjeta, así que no lleva
   ni sombra fuerte ni redondeo (los tenía cuando flotaba sobre el canvas). */
.st-key-nav_rail {{
    position:fixed !important; top:0 !important; left:0 !important; right:0 !important;
    width:100vw !important;
    height:var(--nav-top-alto) !important;
    min-height:var(--nav-top-alto) !important;
    background:#ffffff !important; z-index:999999 !important;
    border:none !important;
    border-bottom:1px solid {GRIS_BORDE} !important;
    border-radius:0 !important;
    box-shadow:none !important;
    /* NAV_X0 alinea el primer reporte con el borde izquierdo de la tarjeta
       (ver la constante). A la derecha basta un respiro para «Refrescar». */
    padding:0 18px 0 {NAV_X0}px !important;
    display:flex !important;
    flex-direction:row !important;
    align-items:center !important;
    /* Si algún día hay tantos reportes que no entran a lo ancho, la fila
       scrollea en vez de desbordar. Sin barra visible: en una franja de 40px
       se comería la mitad del alto. */
    overflow-x:auto !important; overflow-y:hidden !important;
    scrollbar-width:none !important;
}}
.st-key-nav_rail::-webkit-scrollbar {{ height:0 !important; }}

.st-key-nav_rail [data-testid="stVerticalBlock"] {{
    display:flex !important; flex-direction:row !important;
    flex-wrap:nowrap !important;
    align-items:stretch !important; gap:0 !important;
    width:100% !important; height:100% !important;
    min-width:max-content !important;
    padding:0 !important;
    overflow:visible !important;
}}

/* CONTENEDORES DE BOTONES: en fila miden su contenido (en columna medían
   el 100% del rail) y se estiran a lo alto para que el subrayado del activo
   aterrice en el borde inferior de la franja, no a media altura. */
.st-key-nav_rail [data-testid="stElementContainer"],
.st-key-nav_rail [class*="st-key-navbtn_"],
.st-key-nav_rail [data-testid="stButton"] {{
    width:auto !important; min-width:0 !important;
    flex:0 0 auto !important;
    align-self:stretch !important;
    display:flex !important;
    align-items:center !important;
}}

/* LAS TRES CAPAS DEL TOOLTIP. Con `help=`, Streamlit envuelve el botón en
   `div > span.stTooltipIcon > span.stTooltipHoverTarget`, y NINGUNA hereda el
   alto: medido en vivo, el botón medía 14px —lo que su texto— dentro de una
   franja de 40, así que el subrayado del activo y el tinte del hover salían
   como una tira fina a media altura en vez de ocupar la franja entera. En el
   rail vertical no se notaba porque allá el alto lo ponía el propio botón
   (50px fijos) y no había nada que heredar.

   LA COPIA FANTASMA: dentro de un mismo `stButton` con `help=`, Streamlit
   deja DOS hijos — el botón envuelto en el tooltip y una copia suelta sin
   envolver. La copia no está oculta por nada: medía 0x0 sólo porque su alto
   salía del contenido y el rail vertical le daba alto al BOTÓN, no a ella.
   En cuanto la franja horizontal le puso alto y ancho explícitos, la copia
   se dibujó entera y cada reporte apareció DOS VECES, uno al lado del otro.
   Se oculta acotando por la ausencia de tooltip, y sólo cuando hay un
   hermano que sí lo lleva (si algún día un botón va sin `help=`, su único
   hijo no matchea y sigue visible). */
.st-key-nav_rail [class*="st-key-navbtn_"] [data-testid="stButton"]:has(.stTooltipIcon)
    > div:not(:has(.stTooltipIcon)) {{
    display:none !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] [data-testid="stButton"] {{
    align-items:stretch !important;
    height:100% !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] [data-testid="stButton"] > div:has(.stTooltipIcon),
.st-key-nav_rail [class*="st-key-navbtn_"] .stTooltipIcon,
.st-key-nav_rail [class*="st-key-navbtn_"] .stTooltipHoverTarget {{
    display:flex !important;
    align-items:stretch !important;
    height:100% !important;
    width:auto !important;
}}

/* Cada botón -> ítem de menú de TEXTO (2026-08-18; antes tile de ícono).
   Reposo: gris secundario. Hover: tinte lavanda. Activo: texto acento +
   subrayado de 2px pegado al filo de la franja — el mismo tab-subrayado que
   ya usan las franjas de control dentro de las tarjetas (_80_cards.py), así
   que la barra de arriba habla el idioma del resto de la app.
   El subrayado va por `box-shadow: inset` y no por `border-bottom`: no
   participa del box model, así que el texto no se mueve un píxel al
   activarse (con border, los ítems inactivos bailarían 2px). */
.st-key-nav_rail [class*="st-key-navbtn_"] button {{
    width:auto !important; height:100% !important; min-height:0 !important;
    margin:0 !important;
    padding:0 14px !important;
    border:none !important; border-radius:0 !important;
    background:transparent !important; color:{GRIS_TEXTO} !important;
    box-shadow:none !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
    transition:background .2s, color .2s !important;
    flex-shrink:0 !important;
    white-space:nowrap !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button:hover {{
    background:{LAVANDA_FONDO} !important; color:{ACENTO} !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button[kind="primary"] {{
    background:transparent !important; color:{ACENTO_TEXTO} !important;
    box-shadow:inset 0 -2px 0 0 {ACENTO} !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button[kind="primary"]:hover {{
    background:{LAVANDA_FONDO} !important;
}}
/* Etiqueta en LÍNEA (antes apilada bajo el ícono). */
.st-key-nav_rail [class*="st-key-navbtn_"] button p {{
    display:flex !important; flex-direction:row !important;
    align-items:center !important; gap:6px !important;
    font-size:13.5px !important; font-weight:600 !important;
    line-height:1 !important; margin:0 !important;
    white-space:nowrap !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button[kind="primary"] p {{
    font-weight:700 !important;
}}
/* El único ícono que queda en la franja es el de Refrescar (ver abajo). */
.st-key-nav_rail [class*="st-key-navbtn_"] button [data-testid="stIconMaterial"],
.st-key-nav_rail [class*="st-key-navbtn_"] button p > span {{
    font-size:17px !important; line-height:1 !important;
}}

/* Refrescar VIVIÓ ACÁ hasta el 2026-08-22: era la única acción de la franja,
   empujada al extremo derecho con `margin-left:auto`, y arrastraba consigo un
   `stLayoutWrapper > stVerticalBlock` (los dos wrappers que le agrega su
   `st.fragment`) al que había que forzarle el alto para que el hover no
   saliera como una tira fina a media franja.
   Se fue al RAIL DE VISTAS (`graficos/base.py::_render_rail`, key
   `rail_refresh`), a pedido: la franja superior es NAVEGACIÓN pura —una lista
   de reportes— y una acción metida al final se leía como un reporte más.
   En el rail va al pie, bajo una divisoria, que es donde el ojo ya busca las
   acciones. Su CSS vive ahora en estilos/_20_compras_rail.py y su plegado en
   estilos/_25_rails_pestillo.py. Ver arquitectura.md regla #164. */

/* ═══════════════════════════════════════════════════════════════════════
   MÓVIL — la franja superior BAJA y se vuelve barra inferior (bottom nav).
   Es el patrón estándar de apps móviles: la navegación al alcance del
   pulgar. Los botones son LOS MISMOS (mismas keys, mismo estado), solo
   cambian de sitio y de tamaño.
   Acá `--nav-top-alto` vale 0 (_99_movil.py), así que todo lo que el resto
   de `estilos/` corre hacia abajo por la franja vuelve solo a su sitio.
   ═══════════════════════════════════════════════════════════════════════ */
@media (max-width:768px) {{
    /* 1) La franja pasa de arriba a abajo, y crece al alto táctil */
    .st-key-nav_rail {{
        display:flex !important;
        flex-direction:row !important;
        align-items:center !important;
        gap:4px !important;
        top:auto !important; bottom:0 !important; left:0 !important;
        width:100vw !important;
        height:{NAV_MOVIL_ALTO}px !important;
        min-height:{NAV_MOVIL_ALTO}px !important;
        padding:0 !important;
        border:none !important;
        border-top:1px solid {GRIS_BORDE} !important;
        border-radius:0 !important;
        box-shadow:0 -2px 8px rgba(16,16,20,0.08) !important;
        overflow-x:auto !important; overflow-y:hidden !important;
        -webkit-overflow-scrolling:touch !important;
    }}

    /* 2) El bloque interno de botones.
       min-width 100% garantiza que la fila llegue al borde derecho
       aunque haya pocos ítems; max-content permite scroll si hay muchos.
       El padding-right de 150px es una COLA de espacio: Streamlit Cloud
       superpone sus insignias (avatar + "Hosted with Streamlit") sobre la
       esquina inferior derecha; con esta cola, al deslizar hasta el final
       el último ítem queda a la izquierda de esa zona, nunca oculto. */
    .st-key-nav_rail [data-testid="stVerticalBlock"] {{
        flex-direction:row !important;
        gap:4px !important;
        padding:6px 150px 6px 10px !important;
        width:max-content !important;
        min-width:100% !important;
        height:100% !important;
        align-items:center !important;
    }}

    /* 3) Cada wrapper de botón mide 1/4 del viewport: se ven exactamente
       4 ítems a la vez y el resto se alcanza deslizando la barra. */
    .st-key-nav_rail [data-testid="stElementContainer"],
    .st-key-nav_rail [class*="st-key-navbtn_"],
    .st-key-nav_rail [data-testid="stButton"] {{
        width:calc(25vw - 8px) !important;
        flex:0 0 calc(25vw - 8px) !important;
        align-self:center !important;
    }}

    /* 4) Las capas del tooltip vuelven a llenar el ANCHO (en escritorio
       miden su contenido) y sueltan el alto: acá el botón manda con sus
       48px táctiles dentro de una barra de 60. */
    .st-key-nav_rail [class*="st-key-navbtn_"] [data-testid="stButton"],
    .st-key-nav_rail [class*="st-key-navbtn_"] [data-testid="stButton"] > div:has(.stTooltipIcon),
    .st-key-nav_rail [class*="st-key-navbtn_"] .stTooltipIcon,
    .st-key-nav_rail [class*="st-key-navbtn_"] .stTooltipHoverTarget {{
        align-items:center !important;
        height:auto !important;
        width:100% !important;
    }}

    /* 5) El botón llena su wrapper; el área táctil se mantiene sobre 44 px.
       Acá el activo SÍ vuelve a la píldora lavanda: en 25vw de ancho el
       subrayado de escritorio queda demasiado tenue para leerse de un
       vistazo, y la píldora es lo que ya usaban las bottom nav. */
    .st-key-nav_rail [class*="st-key-navbtn_"] button {{
        width:100% !important; height:48px !important; min-height:48px !important;
        padding:0 6px !important;
        border-radius:10px !important;
    }}
    .st-key-nav_rail [class*="st-key-navbtn_"] button[kind="primary"] {{
        background:{LAVANDA_FONDO} !important;
        box-shadow:none !important;
    }}
    /* Etiqueta compacta para la barra inferior */
    .st-key-nav_rail [class*="st-key-navbtn_"] button p {{
        font-size:11px !important;
        gap:2px !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
    }}
    .st-key-nav_rail [class*="st-key-navbtn_"] button [data-testid="stIconMaterial"],
    .st-key-nav_rail [class*="st-key-navbtn_"] button p > span {{
        font-size:18px !important;
    }}
}}
</style>
"""


# ── CSS de la CABECERA FIJA — se inyecta en TODOS los reportes ─────────────
# Nació como override exclusivo de "Ajuste de Inventario" (de ahí el nombre) y
# se universalizó: hoy `inject_navegacion` lo aplica siempre. Sube el contenido
# al tope y deja que el único aire de arriba lo ponga --cab-offset-contenido,
# que cuenta la franja de navegación (--nav-top-alto) y la de fecha/chips.
# Usa "html body ..." para tener MAYOR especificidad que el ".stApp" de _CSS y
# ganar siempre, sin depender del orden de inyección.
_CSS_AJUSTE = """
<style>
/* ── CABECERA FIJA: subir todo el contenido al tope ──────────────────── */

header[data-testid="stHeader"],
[data-testid="stHeader"],
[data-testid="stDecoration"] {
    background: #ffffff !important;
    border-bottom: none !important;
    box-shadow: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
}

/* 1) El aire de arriba lo pone SOLO el block-container (punto 2). */
html body .stApp { padding-top: 0 !important; }

/* 2) Padding superior mínimo del contenedor principal — OVERRIDE POR SECCIÓN
   (nivel 2 de 3; jerarquía en ARQUITECTURA.md). El prefijo `html body` NO es
   decorativo: le da más especificidad que el default global de estilos.py
   (1.5rem) para ganar SIEMPRE, sin depender del orden de inyección. Es el
   mecanismo estándar para overrides por sección en este proyecto.
   Ahora usa la variable definida en estilos.py (--cab-offset-contenido). */
html body [data-testid="stMainBlockContainer"],
html body .stMainBlockContainer,
html body .block-container {
    padding-top: var(--cab-offset-contenido) !important;
}

/* 3) CLAVE: colapsar los contenedores "invisibles" que se apilan arriba
   (st.markdown que solo inyectan <style> y los iframes de overlay/inspector).
   Cada uno aporta un "gap" del bloque vertical y, sumados, forman la franja
   blanca. Ocultar su wrapper elimina ese gap SIN desactivar el CSS (un
   <style> aplica igual aunque esté en display:none). */
html body [data-testid="stElementContainer"]:has([data-testid="stMarkdown"] style),
html body [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
    display: none !important;
}

/* 4) Recorta el desborde lateral de la franja blanca superior
   (.st-key-fila_ajuste_top::before) exactamente al área de contenido.
   `clip` no crea scroll horizontal ni afecta el scroll vertical. */
html body [data-testid="stMain"] { overflow-x: clip !important; }

/* 5) MÓVIL — compactar el aire vertical bajo la cabecera.
   Los wrappers que el punto 3 no alcanza a ocultar (fragmentos, contenedores
   vacíos) miden 0px de alto, pero cada uno añade el row-gap (16px) del bloque
   vertical; encadenados suman una franja vacía antes de los chips/tabla.
   Verificado midiendo el DOM real en viewport 375px. */
@media screen and (max-width: 768px) {
    html body [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
        row-gap: 4px !important;
    }
    html body [data-testid="stMainBlockContainer"],
    html body .stMainBlockContainer,
    html body .block-container {
        padding-top: 108px !important;  /* banda fija (104px) + colchón mínimo */
    }
    /* Compras: en móvil los filtros Familia/Subfamilia YA NO son fijos (fluyen
       en el documento), así que la única cosa fija arriba es el pill de fecha
       (fecha_ajuste_pill, bottom ~50px). La reserva global de 108px deja ~55px
       de banda vacía bajo la fecha. Se recorta a 58px (fecha 50 + 8 de aire).
       Scopeado con :has(.st-key-compras_tabs_row) + mayor especificidad (html
       body + :has) para ganarle a la regla global de arriba. */
    html body [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        [data-testid="stMainBlockContainer"],
    html body [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .block-container {
        padding-top: 58px !important;
    }
}
</style>
"""


@st.fragment
def boton_refresco():
    """Botón de refresco AISLADO en su propio fragment. El clic se maneja
    por VALOR DE RETORNO (no on_click): el rerun sigue siendo SOLO de este
    fragment (la tabla no se re-monta), pero la lógica corre en el cuerpo,
    donde toast/error se pintan de forma fiable. FIX: con on_click dentro
    del fragment el callback no se disparaba (clic perdido en silencio).

    LO DIBUJA EL RAIL DE VISTAS, no esta franja: `graficos/base.py::
    _render_rail` lo llama al pie del rail (ver arquitectura.md regla #164).
    Sigue viviendo acá porque es quien importa la capa de refresco de R2
    (`data.py`) y `graficos/` no la conoce.

    SIN parámetros a propósito: quién es el reporte activo y cuál su parquet
    lo sabe `inject_navegacion`, que corre en app.py:129 —MUCHO antes que el
    rail, dibujado dentro de `_render_contenido()` unas 900 líneas después—.
    Pasarlos por argumento obligaría a que `_render_rail` (compartido por los
    ocho dashboards que lo llaman) los recibiera y los fuera pasando; se
    dejan en `session_state` y el botón los lee al dibujarse."""

    reporte_activo, archivo = st.session_state.get("_ctx_refresco", ("", None))

    pulsado = st.button(
        ":material/refresh: Refrescar",
        key="rail_refresh",
        help=f"Actualizar datos de «{reporte_activo}»",
    )

    if not pulsado:
        return

    if not archivo:
        st.toast("ℹ️ Esta sección no tiene datos propios para actualizar.", icon="ℹ️")
        return

    if not secrets_disponibles():
        limpiar_cache(archivo)
        st.toast("🧪 Modo demo: no hay datos reales para refrescar.", icon="🧪")
        return

    try:
        fecha_conocida = fecha_ultima_actualizacion(archivo)
        ok = solicitar_refresco(archivo, reporte_activo)
    except Exception as e:
        st.error(f"❌ Error al solicitar refresco en R2: {e}")
        return

    if ok:
        st.session_state[f"_refresco_pendiente_{archivo}"] = {
            "reporte": reporte_activo,
            "baseline": fecha_conocida,
            "inicio": datetime.datetime.now(ZONA_PERU),
        }
        st.toast(f"📨 Solicitud enviada para «{reporte_activo}», procesando...", icon="🔄")
    else:
        st.error("⚠️ No se pudo enviar la solicitud de refresco.")


def inject_navegacion(reportes, reporte_activo, mostrar_inspector=False):
    """Dibuja la franja superior de navegación (botones nativos, solo texto).

    Hasta el 2026-08-18 dibujaba además un `#nav-topbar`: una barra fija para
    el título del reporte. Se borró porque llevaba tiempo muerta — el título
    vive en la franja de fecha/chips, así que el topbar salía SIEMPRE vacío y
    con `display:none` desde el CSS de la cabecera."""
    st.markdown(_CSS, unsafe_allow_html=True)

    # DISEÑO UNIFICADO: la cabecera fija (antes exclusiva de Ajuste de
    # Inventario) aplica a TODOS los reportes; el título vive en la franja.
    st.markdown(_CSS_AJUSTE, unsafe_allow_html=True)

    # Contexto del botón de refresco, que YA NO SE DIBUJA ACÁ (2026-08-22):
    # lo dibuja el rail de vistas, mil líneas después en el mismo run. Ver
    # `boton_refresco` arriba y arquitectura.md regla #164.
    st.session_state["_ctx_refresco"] = (
        reporte_activo, reportes.get(reporte_activo, {}).get("archivo"),
    )

    visibles = {
        nombre: info
        for nombre, info in reportes.items()
        if not (nombre == "Inspector" and not mostrar_inspector)
    }

    # Si el reporte activo pertenece a un grupo (p.ej. Receta Base/Venta bajo
    # "Recetas"), recordar CUÁL de sus miembros fue el último visitado: es a
    # dónde navega el botón agrupado la próxima vez que se lo pulse desde
    # otro reporte. Sin esto, el botón siempre volvería al primer miembro del
    # dict, perdiendo en qué sub-reporte estaba el usuario.
    _grupo_activo = visibles.get(reporte_activo, {}).get("grupo_nav")
    if _grupo_activo:
        st.session_state[f"_ultimo_{_grupo_activo}"] = reporte_activo

    # La franja NO se pliega: horizontal, no le quita ancho a la tarjeta, así
    # que no hay nada que recuperar. El pestillo (`pestillos.py`) quedó solo
    # para el rail DERECHO de vistas, que sí compite por el ancho.
    _grupos_dibujados = set()
    with st.container(key="nav_rail"):
        for nombre, info in visibles.items():
            grupo = info.get("grupo_nav")
            if grupo:
                # Un solo botón por grupo — las demás entradas del grupo se
                # saltan (ya comparten etiqueta, no tiene sentido un botón
                # por cada una). Navega al último miembro visitado, o al
                # primero del dict la primera vez.
                if grupo in _grupos_dibujados:
                    continue
                _grupos_dibujados.add(grupo)
                miembros = [n for n, i in visibles.items() if i.get("grupo_nav") == grupo]
                destino = st.session_state.get(f"_ultimo_{grupo}", miembros[0])
                if destino not in miembros:
                    destino = miembros[0]
                st.button(
                    grupo,
                    key=f"navbtn_{_slug(grupo)}",
                    help=grupo,
                    type="primary" if reporte_activo in miembros else "secondary",
                    on_click=_on_nav_click,
                    args=(destino,),
                )
                continue
            # SOLO TEXTO desde el 2026-08-18 (antes ":material/x: etiqueta",
            # con el ícono apilado encima). Respaldo si un reporte nuevo no
            # trae `label_corto`: la primera palabra del nombre, recortada.
            etiqueta = info.get("label_corto") or nombre.split()[0][:10]
            st.button(
                etiqueta,
                key=f"navbtn_{_slug(nombre)}",
                help=nombre,
                type="primary" if nombre == reporte_activo else "secondary",
                on_click=_on_nav_click,
                args=(nombre,),
            )
