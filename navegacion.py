"""
Navegación de la app: Reportes en el RAIL VERTICAL izquierdo, Vistas (dentro
de cada reporte) en la FRANJA HORIZONTAL superior.

2026-08-22 — INVERSIÓN REPORTES ↔ VISTAS
-----------------------------------------
Hasta hoy era al revés: Reportes en la franja superior (desde el
2026-08-18, ver la vuelta anterior de este mismo docstring en el historial
de git) y Vistas en el rail izquierdo. Se invirtió a pedido.

El contenedor por POSICIÓN, no por contenido — mismo criterio que ya usa
este repo con `--rail-der-*` desde el flip de 2026-08-18 (nombre histórico,
comportamiento actual): `compras_tabs_row` sigue siendo LA KEY DEL RAIL
VERTICAL (hoy dibuja Reportes, antes Vistas); `nav_rail` sigue siendo LA KEY
DE LA FRANJA HORIZONTAL (hoy dibuja Vistas — ver `graficos/base.py::
_render_rail` —, antes Reportes). Ningún CSS estructural de `_00_base.py`
se tocó: apunta a la KEY del contenedor, no a su contenido.

2026-08-26 — SE RETIRA EL PLEGADO DEL RAIL VERTICAL
----------------------------------------------------
A pedido ("eliminemos esto y que las filas de los reportes del rail
suban"): se borran `pestillos.py` y `estilos/_25_rails_pestillo.py`
enteros — no quedaba nada más para lo que existieran, era ese único
mecanismo. `compras_tabs_row` ya no dibuja `rail_pestillo` al tope; las
filas de Reportes (en `graf_tipo_chips`) suben a ocupar ese lugar solas,
por ser el mismo `flex-direction: column`. `--rail-der-w` deja de tener un
estado "plegado" que redefinir: vale 280px siempre (`_00_base.py`).

Por qué NO alcanza con "mover el dibujo de sitio": `reporte`/`cfg`/`df_f` se
calculan en app.py ANTES del `@st.fragment` que envuelve
`_render_contenido()`, y quedan capturados en su closure. Un clic en
Reportes tiene que disparar un RERUN COMPLETO (para que esos tres se
recalculen) — por eso `inject_navegacion()` sigue llamándose en app.py:129,
en el mismo punto de ejecución de siempre, ANTES del fragment, aunque ahora
dibuje en el contenedor vertical en vez del horizontal. Si Reportes se
dibujara dentro del fragment (junto a Vistas), un clic solo re-ejecutaría el
fragment: el botón se vería activo pero `df_f` quedaría congelado en el
reporte anterior — bug silencioso, no un error visible.

ÍCONOS: `data.py::REPORTES[x]["icono"]` volvió a usarse (estaba parqueado
sin consumidor desde el 2026-08-18) — son shortcodes Material Symbols
válidos, no los nombres de Bootstrap Icons que tenía antes de esa fecha
(revalidados/traducidos el 2026-08-22, ver el propio dict). El rail
vertical reusa el CSS de "lista con ícono+chevron+hairline" que ya existía
en estilos/_20_compras_rail.py para Compras — generalizado (se le sacó el
scope a Compras: ver ese archivo) porque ahora aplica siempre, a Reportes.

KPIS: cada ítem del rail suma una segunda línea chica con 1-3 KPIs del
reporte (ver `data.py::resumen_kpis`, agregado DuckDB barato contra R2, sin
descargar el parquet completo). Viven en `REPORTES[x]["kpis"]`.

Implementación con BOTONES NATIVOS de Streamlit (sin iframes ni manipulación
del DOM): el click lo maneja Streamlit directamente vía on_click, por lo que
cambiar de reporte es fiable en cada pulsación (no se cuelga ni "deja de
hacer caso"). app.py lee la selección desde st.session_state["_nav_reporte"].
"""

import re
import streamlit as st
import datetime
from zoneinfo import ZoneInfo
from data import (
    solicitar_refresco, secrets_disponibles, fecha_ultima_actualizacion,
    limpiar_cache, resumen_kpis,
)
from utils import fmt_k
from tema import GRIS_BORDE

ZONA_PERU = ZoneInfo("America/Lima")

# Sufijo de unidad para los KPIs que son un CONTEO (no un monto — esos usan
# fmt_k, que ya trae su propio "S/"). Vive acá y no en data.py::REPORTES
# porque es un detalle de PRESENTACIÓN, no del dato: la query de
# resumen_kpis() no necesita saber cómo se va a mostrar el número.
_SUFIJO_KPI = {
    "Documentos": "docs", "Requerim.": "reqs", "Recetas": "recetas",
    "Platos": "platos", "Pax": "pax",
}


def _slug(s):
    return re.sub(r'[^a-zA-Z0-9]+', '_', s)


def _on_nav_click(nombre):
    """Guarda el reporte elegido. Corre ANTES del script => app.py lo ve desde
    arriba en un solo rerun."""
    st.session_state["_nav_reporte"] = nombre


def _formatear_kpis(info):
    """(primario, secundario) para el ítem del rail — estilo lista de
    cotizaciones (referencia: el panel "Vistos recientemente" de MSN Money,
    a pedido 2026-08-22): el NOMBRE va a la izquierda, los NÚMEROS a la
    derecha en dos renglones — grande arriba, chico y apagado abajo. No es
    una línea `· `-separada como la primera versión: esa se leía flotando
    entre dos filas sin quedar claro de cuál era, porque no compartía
    renglón con su nombre. Acá los dos textos se superponen en la MISMA
    fila del botón vía CSS (`position:absolute`) — ver el contenedor
    `navitem_<slug>` que los envuelve a los dos en `inject_navegacion`.

    `secundario` es None cuando el reporte define un solo KPI (Ajuste,
    Inventario, Receta Base/Venta): no hay nada natural que poner en el
    segundo renglón, y dejarlo vacío se lee mejor que inventar un dato.

    Caso especial VENTAS: si el reporte trae "Venta" Y "Pax" (únicos dos
    KPIs que hoy comparten reporte), el secundario suma un tercer valor
    DERIVADO —Ticket promedio = Venta / Pax— que no sale de ninguna
    columna del parquet por sí sola. No hay una forma genérica de expresar
    "un KPI es la razón entre otros dos" en `REPORTES[x]["kpis"]` que
    valga la pena para un solo caso; se resuelve acá, a mano, igual que ya
    hace `graficos/ventas_resumen.py` con el mismo cálculo.

    Retorna `None` (no una tupla) si no definió `kpis`, si la consulta no
    trajo nada (parquet sin esa columna, R2 caído — resumen_kpis() ya
    devuelve {} en esos casos) o si es la primera carga y todavía no hay
    nada cacheado.

    Tercer elemento `negativo`: True si el KPI primario es un monto
    (`sum`) con signo negativo — hoy sólo le pasa a Ajuste Valorizado
    (mermas), pero se detecta genérico por signo, no por nombre de
    reporte, para no hardcodear qué reporte puede ir negativo. Referencia
    MSN Money, a pedido 2026-08-22: el delta ahí se colorea por signo, acá
    el equivalente es el monto mismo (el rail no tiene "vs. período
    anterior" para calcular un delta real)."""
    kpis = info.get("kpis")
    if not kpis:
        return None
    valores = resumen_kpis(info["archivo"], kpis,
                           info.get("kpi_fecha"), info.get("kpi_dedup"))
    if not valores:
        return None

    def _fmt(etiqueta, agregacion, v):
        if agregacion == "sum":
            return fmt_k(v)
        suf = _SUFIJO_KPI.get(etiqueta, "")
        return f"{v:,.0f}{(' ' + suf) if suf else ''}"

    items = [(et, ag, valores[et])
             for et, _col, ag in kpis if valores.get(et) is not None]
    if not items:
        return None
    partes = [_fmt(et, ag, v) for et, ag, v in items]
    if "Venta" in valores and "Pax" in valores and valores["Pax"]:
        partes.append(f"S/ {valores['Venta'] / valores['Pax']:.1f}")
    primario, resto = partes[0], partes[1:]
    negativo = items[0][2] < 0
    return primario, (" · ".join(resto) if resto else None), negativo


# ── CSS de la FRANJA HORIZONTAL (hoy: Vistas) ───────────────────────────
# Vivía acá cuando esta franja dibujaba Reportes (hasta el 2026-08-22); se
# queda en el MISMO archivo tras la inversión (regla #170) porque el
# contrato de click y el de estilo de "fila de tabs de texto" siguen siendo
# los de este módulo — lo único que cambió es QUIÉN la inyecta:
# `graficos/base.py::_render_rail` (Vistas, el nuevo dueño del contenido de
# `nav_rail`) la importa y la inyecta en cada uno de sus 9 call sites, en
# vez de `inject_navegacion` inyectarla una sola vez. CSS igual, disparador
# distinto — es lo esperable dado que ahora el contenido de la franja
# depende de qué REPORTE está activo, y no se conoce hasta adentro del
# fragment de cada dashboard.
#
# Generalizada: los 9 `_render_rail(...)` traen `btn_prefix` propios por
# dashboard (`aj_rail_btn_`, `ventas_rail_btn_`, …, no todos `navbtn_`). En
# vez de forzar los 9 call sites a un prefijo común, se le sacó a esta CSS
# la dependencia del prefijo literal — matchea por `data-testid`
# estructural, sin filtrar por clase de key.
#
# Se le sacó también la defensa "tres capas del tooltip / copia fantasma"
# que traía cuando dibujaba Reportes: esa trampa la dispara `help=`, que
# Reportes usaba y Vistas nunca usó. Reportes se llevó la defensa consigo a
# estilos/_20_compras_rail.py (scopeada a `graf_tipo_chips`, su nuevo hogar).
# Donde `inject_navegacion` deja la cabecera del reporte activo (nombre +
# KPIs ya formateados). La lee el rail de vistas de `graficos/base.py`.
# Nombre de la app, para el titulo de la franja. Vive aca porque aca se sabe
# cual es el reporte activo, que es la otra mitad del titulo.
APP_NOMBRE = "Sapiens"

CLAVE_CABECERA = "_nav_cabecera"

NAV_X0 = 64        # Ver comentario original más abajo, junto al CSS.
NAV_MOVIL_ALTO = 60  # Debe coincidir con estilos/_00_base.py, ver ese archivo.

_CSS_FRANJA_VISTAS = f"""
<style>
/* Contenedor -> FRANJA HORIZONTAL fija arriba, de borde a borde. Blanca con
   una línea inferior: es cromo, no una tarjeta, así que no lleva ni sombra
   fuerte ni redondeo. */
.st-key-nav_rail {{
    /* DOS FILAS, no una (2026-08-25, a pedido, con captura del modo diseno):
           fila 1  ->  Familia / Subfamilia / chips del drill
           fila 2  ->  Proveedor · Producto · Vs ano pasado · ...
       Esta franja es la SEGUNDA, asi que baja `--nav-top-alto + 8px`: los
       chips se quedan con la banda de arriba (`_50_fecha.py`,
       `_40_ajuste_franja.py`).

       Hubo un intento de meter las dos cosas en la MISMA linea y no entra:
       los 7 botones de vista miden 634px y los chips 615, con 943
       disponibles a 1356 de ancho — 306px de superposicion, medido.

       Al entrar en la banda blanca pierde su fondo y su linea: esa banda ya
       los pinta (`fila_ajuste_top::before`), y superponerlos daba dos bordes
       a 8px de distancia. */
    position:fixed !important;
    top:calc(var(--nav-top-alto) + 8px) !important;
    left:0 !important; right:0 !important;
    width:100vw !important;
    height:var(--nav-top-alto) !important;
    min-height:var(--nav-top-alto) !important;
    /* BLANCA, la suya (2026-08-25). Estuvo en `transparent` mientras la
       banda de atras era blanca y la pintaba por ella; al pasar esa banda
       al color del lienzo (`--bg-primary`, `_40_ajuste_franja.py`) esta
       fila se volvio gris con ella, y no era el pedido: la fila de las
       PESTANAS es blanca. Ahora cada una pone su color — el lienzo detras
       del titulo y los filtros, blanco detras de las vistas. */
    background:var(--bg-card) !important; z-index:999999 !important;
    border:none !important;
    /* Línea delgada SOLO abajo (2026-08-26, a pedido: "una idea visual de
       separación"). Antes esta fila y lo que scrollea debajo compartían el
       mismo blanco sin ningún borde entre las dos — el usuario tenía que
       adivinar dónde terminaba el cromo fijo y empezaba el contenido. Va
       encima del `border:none` de arriba (mismo shorthand, dos
       declaraciones, gana la última) y no reemplaza ese `none`: así un
       cambio futuro de los otros tres lados no reabre esta línea por
       accidente. Mismo `--border` que usa el resto de la app para
       divisorias finas (`_00_base.py`), no un gris propio. */
    border-bottom:1px solid var(--border) !important;
    border-radius:0 !important;
    box-shadow:none !important;
    /* NAV_X0 es el sangrado de MÓVIL, donde esta barra se va al pie y ocupa
       todo el ancho. En escritorio manda el bloque de abajo. */
    padding:0 18px 0 {NAV_X0}px !important;
    display:flex !important;
    flex-direction:row !important;
    align-items:center !important;
    overflow-x:auto !important; overflow-y:hidden !important;
    scrollbar-width:none !important;
}}
.st-key-nav_rail::-webkit-scrollbar {{ height:0 !important; }}

/* EN ESCRITORIO LA FRANJA ARRANCA DONDE ARRANCAN LAS TARJETAS (2026-08-25,
   a pedido). Antes empezaba pegada al borde izquierdo, o sea ENCIMA de la
   columna del rail de reportes, y los nombres de las vistas quedaban sobre
   una columna con la que no tienen nada que ver.

   `--rail-der-res` y no un número: es el ancho que el contenido YA le
   reserva a esa columna (`_00_base.py`, derivado de `--rail-der-w`), así
   que los nombres caen exactamente sobre el borde izquierdo de las
   tarjetas. Y como la variable sigue al rail, si el rail se pliega
   (pestillo, `_25_rails_pestillo.py`) la franja se corre con él sola.

   Sólo escritorio: en móvil esta barra es la nav inferior y ocupa el ancho
   completo — ahí manda el padding de arriba. Mismo breakpoint que el resto
   del proyecto. */
@media screen and (min-width: 769px) {{
    .st-key-nav_rail {{
        /* La franja EMPIEZA Y TERMINA con las tarjetas (2026-08-25, a
           pedido). Antes iba de borde a borde (`left:0; right:0;
           width:100vw`) y su blanco se derramaba mas alla del contenido —
           por la izquierda sobre la columna del rail, por la derecha hasta
           el filo de la ventana.

           Las dos anclas son las MISMAS que usan la banda de atras y las
           tarjetas: `--rail-der-res` (lo que el contenido le reserva a la
           columna) y los 90px del margen derecho. Asi las tres capas
           comparten linea, que es la regla #137 del proyecto.

           `left` reemplaza al `padding-left` que habia aca: con la caja ya
           acotada, el padding sobraba y desplazaba los botones el doble. */
        left: var(--rail-der-res) !important;
        right: 90px !important;
        width: auto !important;
        padding-left: 0 !important;
    }}
}}

/* LA FILA ES `.st-key-nav_rail` MISMO, no un hijo suyo.
   `st.container(key="nav_rail")` renderiza UN stVerticalBlock que ya lleva
   la key, y `_render_rail` mete los botones DIRECTOS adentro (sin wrapper
   propio, ver su docstring). Hasta el 2026-08-24 estas declaraciones
   colgaban de `.st-key-nav_rail [data-testid="stVerticalBlock"]`, un
   DESCENDIENTE que no existe: el selector no matcheaba nada, el `gap:0` se
   perdía y sobrevivía el `gap:1rem` propio de Streamlit. Con 8 vistas son
   7 huecos = 112px de más, y el último ítem ("Tabla") se salía de un
   viewport de 900px — medido, borde derecho en x=924. Se listan LOS DOS
   selectores a propósito: si alguna vez vuelve a haber un wrapper interno,
   tampoco puede reintroducir el hueco. Ver arquitectura.md regla #201.
   Ojo con lo que NO se hereda de la regla vieja: `min-width:max-content`
   servía para un wrapper y sobre el rail sería un bug — lo estiraría hasta
   el ancho del contenido y anularía el `overflow-x:auto` que hace de
   válvula en viewports angostos. */
.st-key-nav_rail,
.st-key-nav_rail [data-testid="stVerticalBlock"] {{
    flex-wrap:nowrap !important;
    gap:0 !important; row-gap:0 !important; column-gap:0 !important;
}}

/* CONTENEDORES DE BOTONES: en fila miden su contenido y se estiran a lo
   alto para que el subrayado del activo aterrice en el borde inferior de
   la franja, no a media altura. */
.st-key-nav_rail [data-testid="stElementContainer"],
.st-key-nav_rail [data-testid="stButton"] {{
    width:auto !important; min-width:0 !important;
    flex:0 0 auto !important;
    align-self:stretch !important;
    display:flex !important;
    align-items:center !important;
}}
.st-key-nav_rail [data-testid="stButton"] {{
    align-items:stretch !important;
    height:100% !important;
}}

/* Cada botón -> ítem de menú de TEXTO. Reposo: gris secundario. Hover:
   tinte lavanda. Activo: texto acento + subrayado de 2px pegado al filo de
   la franja — mismo tab-subrayado que las franjas de control dentro de las
   tarjetas (_80_cards.py). El subrayado va por `box-shadow: inset` y no por
   `border-bottom`: no participa del box model, el texto no se mueve un
   píxel al activarse. */
.st-key-nav_rail [data-testid="stButton"] button {{
    width:auto !important; height:100% !important; min-height:0 !important;
    margin:0 !important;
    padding:0 14px !important;
    border:none !important; border-radius:0 !important;
    background:transparent !important; color:var(--text-secondary) !important;
    box-shadow:none !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
    transition:background .2s, color .2s !important;
    flex-shrink:0 !important;
    white-space:nowrap !important;
}}
.st-key-nav_rail [data-testid="stButton"] button:hover {{
    background:var(--accent-tint) !important; color:var(--accent) !important;
}}
.st-key-nav_rail [data-testid="stButton"] button[kind="primary"] {{
    background:transparent !important; color:var(--accent-deep) !important;
    box-shadow:inset 0 -2px 0 0 var(--accent) !important;
}}
.st-key-nav_rail [data-testid="stButton"] button[kind="primary"]:hover {{
    background:var(--accent-tint) !important;
}}
.st-key-nav_rail [data-testid="stButton"] button p {{
    display:flex !important; flex-direction:row !important;
    align-items:center !important; gap:6px !important;
    font-size:13.5px !important; font-weight:600 !important;
    line-height:1 !important; margin:0 !important;
    white-space:nowrap !important;
}}
.st-key-nav_rail [data-testid="stButton"] button[kind="primary"] p {{
    font-weight:700 !important;
}}

/* ═══════════════════════════════════════════════════════════════════════
   MÓVIL — la franja superior BAJA y se vuelve barra inferior (bottom nav).
   Acá `--nav-top-alto` vale 0 (_99_movil.py), así que todo lo que el resto
   de `estilos/` corre hacia abajo por la franja vuelve solo a su sitio.
   ═══════════════════════════════════════════════════════════════════════ */
@media (max-width:768px) {{
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
    /* El gemelo móvil de la regla muerta de arriba: mismo selector
       descendiente inexistente, mismo efecto nulo. No se resucita ninguna
       de sus declaraciones porque el rail YA las trae puestas sobre sí
       mismo (flex-direction:row, gap:4px, align-items:center) y borrarlas
       es un no-op medido. La única que pedía algo distinto era
       `padding:6px 150px 6px 10px`: reservaba 150px a la derecha para un
       flotante que hoy no está ahí (medido a 375px: no hay ningún `fixed`
       en esa esquina). Llevaba muerta desde la inversión Reportes/Vistas
       del 2026-08-22 sin que nadie la extrañara, así que se va con el resto
       en vez de reaparecer de golpe como un hueco de 150px. */
    .st-key-nav_rail [data-testid="stElementContainer"],
    .st-key-nav_rail [data-testid="stButton"] {{
        width:calc(25vw - 8px) !important;
        flex:0 0 calc(25vw - 8px) !important;
        align-self:center !important;
    }}
    .st-key-nav_rail [data-testid="stButton"] button {{
        width:100% !important; height:48px !important; min-height:48px !important;
        padding:0 6px !important;
        border-radius:10px !important;
    }}
    .st-key-nav_rail [data-testid="stButton"] button[kind="primary"] {{
        background:var(--accent-tint) !important;
        box-shadow:none !important;
    }}
    .st-key-nav_rail [data-testid="stButton"] button p {{
        font-size:11px !important;
        gap:2px !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
    }}
}}
</style>
"""


# ── CSS del RAIL VERTICAL (hoy: Reportes) ───────────────────────────────
# El ANCHO/posición/pestillo/breakpoint móvil son de `estilos/_20_compras_
# rail.py` + `_25_rails_pestillo.py` (contenedor por POSICIÓN, ver docstring
# del módulo) — no se duplican acá. Lo único propio de Reportes son los
# KPIs, que no existían antes de este cambio.
#
# 2026-08-22, segunda vuelta: la primera versión dibujaba los KPIs como una
# TERCERA LÍNEA suelta debajo del botón (un `st.markdown` hermano) —
# reportado con captura: "no se ve bien", el texto quedaba flotando entre
# dos filas sin quedar claro a cuál pertenecía. A pedido, se rehace tomando
# de referencia el panel "Vistos recientemente" de MSN Money: nombre a la
# IZQUIERDA, valores a la DERECHA en la MISMA fila (grande arriba, chico y
# apagado abajo).
#
# `st.button()` ESCAPA el HTML de su label — verificado en vivo (server de
# prueba descartable, `<span style="...">` salió como texto literal
# `&lt;span...&gt;`, no como HTML — no hay forma de meter los valores
# DENTRO del botón. La solución es superponerlos: cada ítem del rail se
# envuelve en su PROPIO `st.container(key=f"navitem_{slug}")`
# (`inject_navegacion`, más abajo) — eso da un ancestro común real para
# `position:relative`, y los valores se posicionan `absolute` sobre la
# esquina derecha de esa misma caja, centrados verticalmente contra el
# alto del botón. Sin el contenedor por ítem no hay ancestro que compartan
# el botón y su texto de valores (son hermanos sueltos en el flujo), y
# `position:absolute` necesita ANCLAR contra algo.
_CSS_KPIS = """
<style>
.st-key-graf_tipo_chips [class*="st-key-navitem_"] {
    position: relative !important;
}
/* Streamlit le da `position:relative` a TODO stElementContainer por
   defecto (para sus propias decoraciones internas — toolbar, etc.), y ese
   wrapper del st.markdown (alto 0, más CERCANO en el DOM a .nav-kpis-
   valores que el propio navitem_) se cuela como ancla del `position:
   absolute` antes de llegar a navitem_ — medido en vivo: el valor
   aparecía centrado contra una caja de 0px de alto en vez del botón de
   40px, corrido hacia abajo. Se apaga SOLO en el contenedor que envuelve
   a `.nav-kpis-valores` (con `:has()`, no en TODOS los stElementContainer
   del navitem_ — el del botón necesita el suyo para sus propias
   decoraciones) para que `position:absolute` salte a `navitem_`, que es
   el ancla que sí tiene el alto correcto. */
.st-key-graf_tipo_chips [class*="st-key-navitem_"]
    [data-testid="stElementContainer"]:has(.nav-kpis-valores) {
    position: static !important;
}
/* Hermano del boton (st.markdown propio dentro del mismo navitem_). La
   regla "NUCLEAR" de estilos/_20_compras_rail.py excluye esta clase de su
   zeroing de margin/padding — si no, perdía la pelea de especificidad. */
.st-key-graf_tipo_chips .nav-kpis-valores {
    display: block !important;
    position: absolute !important;
    right: 12px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    text-align: right !important;
    max-width: 46% !important;
    pointer-events: none !important;   /* no le roba el clic al boton de abajo */
}
.st-key-graf_tipo_chips .nav-kpis-primario {
    display: block !important;
    font-size: 14px !important;   /* 2026-08-23: 12px + ~20%, junto con el rail */
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    line-height: 1.3 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
.st-key-graf_tipo_chips .nav-kpis-secundario {
    display: block !important;
    font-size: 11.5px !important;   /* 2026-08-23: 9.5px + ~20% */
    font-weight: 400 !important;
    color: var(--text-muted) !important;
    line-height: 1.3 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
/* Sobre fondo activo (accent-light) el texto muted pierde contraste —
   mismo tratamiento que el label del botón en ese estado. El botón y el
   texto de valores NO son hermanos directos (cada uno cuelga de su propio
   stElementContainer dentro de navitem_), así que no sirve un combinador
   `~` entre ellos: se sube al ANCESTRO común (`navitem_`) con `:has()` y
   se baja de nuevo a los dos textos. */
.st-key-graf_tipo_chips [class*="st-key-navitem_"]:has(button[kind="primary"])
    .nav-kpis-primario,
.st-key-graf_tipo_chips [class*="st-key-navitem_"]:has(button[kind="primary"])
    .nav-kpis-secundario {
    color: var(--accent-deep) !important;
}
/* KPI primario negativo (hoy: sólo Ajuste Valorizado, ver docstring de
   _formatear_kpis) — referencia MSN Money, 2026-08-22, medido en vivo con
   sus propias herramientas de desarrollador: rgb(209,52,56) para el
   descenso. Acá se reusa --danger-text en vez de ese literal (CLAUDE.md:
   "nunca un #hex suelto"; es el mismo par que ya usa Ajuste para sus
   mermas/sobrantes). El segundo selector repite el de "activo" arriba +
   `.kpi-neg`: a propósito MÁS específico que ese, así el rojo gana incluso
   si el reporte negativo (Ajuste) está también activo. */
.st-key-graf_tipo_chips .nav-kpis-primario.kpi-neg,
.st-key-graf_tipo_chips [class*="st-key-navitem_"]:has(button[kind="primary"])
    .nav-kpis-primario.kpi-neg {
    color: var(--danger-text) !important;
}
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
    fragment, pero la lógica corre en el cuerpo, donde toast/error se pintan
    de forma fiable. FIX: con on_click dentro del fragment el callback no se
    disparaba (clic perdido en silencio).

    LO DIBUJA inject_navegacion, al pie del rail de Reportes (ver más abajo)
    — volvió ahí el 2026-08-22 al invertirse Reportes↔Vistas (arquitectura.md
    regla #170): la acción vive donde vive el rail VERTICAL, sea cual sea su
    contenido, porque es "el pie de una lista", no "lo último de Reportes"
    ni "lo último de Vistas". Su CSS (`.st-key-rail_refresh`) no se tocó —
    vive en estilos/_20_compras_rail.py, scopeado a la KEY del contenedor,
    no a lo que dibuja adentro.

    SIN parámetros a propósito: quién es el reporte activo y cuál su parquet
    lo sabe `inject_navegacion`, que los setea en session_state ANTES de
    llamar a este fragment, en la misma función."""

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
    """Dibuja Reportes en el RAIL VERTICAL (key `compras_tabs_row`).

    Hasta el 2026-08-22 dibujaba la franja HORIZONTAL (key `nav_rail`) —
    ver el docstring del módulo para el porqué de la inversión y por qué
    esta función se sigue llamando en el MISMO punto de app.py (línea 129,
    antes del fragment) aunque cambió qué contenedor dibuja.

    Hasta el 2026-08-18 dibujaba además un `#nav-topbar`: una barra fija para
    el título del reporte. Se borró porque llevaba tiempo muerta — el título
    vive en la franja de fecha/chips, así que el topbar salía SIEMPRE vacío y
    con `display:none` desde el CSS de la cabecera."""
    st.markdown(_CSS_KPIS, unsafe_allow_html=True)

    # DISEÑO UNIFICADO: la cabecera fija (antes exclusiva de Ajuste de
    # Inventario) aplica a TODOS los reportes; el título vive en la franja.
    st.markdown(_CSS_AJUSTE, unsafe_allow_html=True)

    # Contexto del botón de refresco: se dibuja al PIE de este mismo rail,
    # más abajo en esta misma función (ver boton_refresco()).
    st.session_state["_ctx_refresco"] = (
        reporte_activo, reportes.get(reporte_activo, {}).get("archivo"),
    )

    visibles = {
        nombre: info
        for nombre, info in reportes.items()
        if not (nombre == "Inspector" and not mostrar_inspector)
    }

    # ── Cabecera del reporte activo, para quien la quiera repetir ────────
    # La consume el rail VERTICAL de vistas (`graficos/base.py::_render_rail`)
    # para encabezarse con "dónde estás" cuando reemplaza a esta lista al
    # bajar: sin eso la columna cambia de contenido y se pierde el nombre del
    # reporte, que es justo el contexto que el usuario venía leyendo.
    #
    # Va por `session_state` y no por un import: `base.py` no conoce
    # `REPORTES` y no tiene por qué: acá ya está resuelto cuál es el activo
    # y sus KPIs ya están formateados por `_formatear_kpis`. Duplicar esa
    # lógica del otro lado era garantizar que se desincronicen.
    _info_act = visibles.get(reporte_activo, {})
    _par_act = _formatear_kpis(_info_act) if not _info_act.get("tool") else None
    st.session_state[CLAVE_CABECERA] = {
        "nombre": reporte_activo,
        "icono": _info_act.get("icono"),
        "primario": _par_act[0] if _par_act else None,
        "secundario": _par_act[1] if _par_act else None,
        "negativo": bool(_par_act[2]) if _par_act else False,
    }

    # Si el reporte activo pertenece a un grupo (p.ej. Receta Base/Venta bajo
    # "Recetas"), recordar CUÁL de sus miembros fue el último visitado: es a
    # dónde navega el botón agrupado la próxima vez que se lo pulse desde
    # otro reporte. Sin esto, el botón siempre volvería al primer miembro del
    # dict, perdiendo en qué sub-reporte estaba el usuario.
    _grupo_activo = visibles.get(reporte_activo, {}).get("grupo_nav")
    if _grupo_activo:
        st.session_state[f"_ultimo_{_grupo_activo}"] = reporte_activo

    # ── Titulo de la franja: app + reporte ───────────────────────────────
    # "Sapiens (Compras)", al estilo de las fichas de MSN Dinero
    # ("Ferreycorp SAA (FERREYC1)"): la entidad primero, su codigo entre
    # parentesis. Ocupa la esquina izquierda de la FILA 1, donde antes vivia
    # el titulo fantasma del drill (`compras_prov_titulo_franja`) — ese
    # decia el nombre de la vista, que ya lo dice la pestana activa de la
    # fila 2, y encima se le superponia.
    #
    # Se dibuja aca y no en cada dashboard porque es informacion del
    # REPORTE, no de la vista: quien la sabe es esta funcion.
    st.markdown(
        f'<div class="franja-titulo-app">{APP_NOMBRE}'
        f' <span class="franja-titulo-rep">({reporte_activo})</span></div>',
        unsafe_allow_html=True,
    )

    # ── Rótulo de la columna ─────────────────────────────────────────────
    # "Reportes", FUERA de la tarjeta, en el hueco que el rail dejó libre
    # arriba al bajar a top:47px. Es el "Vistos recientemente" que encabeza
    # la lista de MSN Dinero — el mismo modelo del que salió esta columna
    # entera: dice qué es la lista sin gastar una fila de adentro.
    #
    # Su gemelo ("Vistas") lo dibuja `graficos/base.py::_render_rail` para el
    # otro rail, y los dos se cruzan con el mismo `rails-scrolled` que cruza
    # a los railes. Geometría en `estilos/_20_compras_rail.py`, cruce en
    # `estilos/_26_rails_scroll.py`.
    with st.container(key="rail_rotulo_rep"):
        st.markdown('<div class="rail-rotulo">Reportes</div>',
                    unsafe_allow_html=True)

    _grupos_dibujados = set()
    with st.container(key="compras_tabs_row"):
        with st.container(key="graf_tipo_chips"):
            for nombre, info in visibles.items():
                grupo = info.get("grupo_nav")
                if grupo:
                    # Un solo botón por grupo — las demás entradas del grupo
                    # se saltan (ya comparten etiqueta, no tiene sentido un
                    # botón por cada una). Navega al último miembro
                    # visitado, o al primero del dict la primera vez.
                    if grupo in _grupos_dibujados:
                        continue
                    _grupos_dibujados.add(grupo)
                    miembros = [n for n, i in visibles.items()
                               if i.get("grupo_nav") == grupo]
                    destino = st.session_state.get(f"_ultimo_{grupo}", miembros[0])
                    if destino not in miembros:
                        destino = miembros[0]
                    # navitem_<slug> es el ancestro común que necesita el CSS
                    # de los valores (position:relative + el :has() del
                    # estado activo) — ver el docstring de _CSS_KPIS. Los
                    # grupos no tienen KPI propio (¿de cuál de sus miembros
                    # sería? Movimientos = Salidas + Requerimientos, no hay
                    # una respuesta sin ambigüedad) así que este contenedor
                    # sólo envuelve al botón, pero se mantiene por
                    # UNIFORMIDAD: el hairline entre ítems (estilos/_20_
                    # compras_rail.py) asume que cada reporte es exactamente
                    # un `navitem_`, agrupado o no.
                    with st.container(key=f"navitem_{_slug(grupo)}"):
                        st.button(
                            grupo,
                            key=f"navbtn_{_slug(grupo)}",
                            help=grupo,
                            icon=info.get("icono"),
                            type="primary" if reporte_activo in miembros else "secondary",
                            use_container_width=True,
                            on_click=_on_nav_click,
                            args=(destino,),
                        )
                    continue
                etiqueta = info.get("label_corto") or nombre.split()[0][:10]
                with st.container(key=f"navitem_{_slug(nombre)}"):
                    st.button(
                        etiqueta,
                        key=f"navbtn_{_slug(nombre)}",
                        help=nombre,
                        icon=info.get("icono"),
                        type="primary" if nombre == reporte_activo else "secondary",
                        use_container_width=True,
                        on_click=_on_nav_click,
                        args=(nombre,),
                    )
                    # Valores del KPI, superpuestos a la derecha de ESTE
                    # MISMO botón vía CSS — ver el docstring de _CSS_KPIS
                    # para por qué no van dentro del label (st.button
                    # escapa el HTML) y por qué hace falta el
                    # `navitem_<slug>` que los envuelve a los dos.
                    par = _formatear_kpis(info) if not info.get("tool") else None
                    if par:
                        primario, secundario, negativo = par
                        clase_primario = "nav-kpis-primario kpi-neg" if negativo else "nav-kpis-primario"
                        st.markdown(
                            '<div class="nav-kpis-valores">'
                            f'<span class="{clase_primario}">{primario}</span>'
                            + (f'<span class="nav-kpis-secundario">{secundario}</span>'
                               if secundario else '')
                            + '</div>',
                            unsafe_allow_html=True,
                        )
        # PIE DEL RAIL — Refrescar, la única ACCIÓN (no un reporte). Fuera de
        # graf_tipo_chips por lo mismo que el pestillo (regla #6).
        boton_refresco()
