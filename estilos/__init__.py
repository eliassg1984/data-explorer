"""
Estilos globales de la app: CSS, tamaños de fuente e inyección del tema.

ÍNDICE — un módulo por sección, el prefijo numérico marca el orden
------------------------------------------------------------------
    _00_base            paleta :root, tipografía, layout raíz, inputs,
                        botones, expander, alertas, header nativo
    _20_compras_rail    rail vertical derecho (selector de gráfico) —
                        compartido por TODOS los reportes pese al nombre
    _30_filtros         botón/popover de filtros
    _40_ajuste_franja   franja superior sticky + chips de filtro
    _50_fecha           pill de fecha y su panel (atajos + calendario)
    _60_calendario      calendario desplegable (BaseWeb)
    _70_chrome          ocultar toolbars nativas, posición del toast
    _80_cards           cards de gráficos + tarjetas del drill de Proveedor
    _90_franja_inferior franja inferior fija
    _99_movil           overrides @media (SIEMPRE al final; no mover)

Para ubicar una regla: `grep` el prefijo de la key en `estilos/`. No hay
números de línea que mantener — el nombre del módulo es el índice.

Convención de keys — CRÍTICO para evitar solapes
------------------------------------------------
Un elemento visual = UNA key que es dueña de su estilo.

- La key dueña vive en un `st.container(key="…")` que envuelve al elemento.
- Los WIDGETS (`st.date_input`, `st.pills`, `st.selectbox`) NO se estilan
  por su propia key — se envuelven en un container con key propia y se
  estila el container. Ese container es el único bloque CSS que existe.
- Antes de agregar CSS para un elemento nuevo: `grep -n <key-prefix>`
  aquí; si ya hay otro bloque estilándolo, consolidar en UNO — no dejar
  dos rutas de estilado para el mismo elemento (misma especificidad +
  ambos `!important` = gana el que aparezca ÚLTIMO en el archivo, y eso
  es un bug esperando a pasar).

Sobre los `!important` (hoy hay ~450)
-------------------------------------
Casi todos son `!important` LEGÍTIMOS, no deuda: los usamos para ganarle
en especificidad a las clases internas que Streamlit inyecta. Reducir el
número por sí solo no aporta nada. Lo que sí importa:

- Cuando una regla ANULA algo que Python declaró (ej. `st.container(border=
  True)` cuyo borde tapas con `border: none !important`), documentar el
  POR QUÉ arriba de la regla. Un `!important` sin comentario adyacente
  es aceptable; uno que contradice al código Python NO.
- Cuando un cambio de diseño hace innecesario un bloque, borrarlo — no
  dejarlo "por si acaso". Los parches olvidados generan bugs futuros
  (ver commit de bordes del drill Proveedor 2026-07-25, y solape de
  `fch_franja_` vs `fecha_ajuste_pill` 2026-07-26).

Sobre st.pills (importante para futuros cambios de estilo)
----------------------------------------------------------
En la versión actual de Streamlit, st.pills renderiza este DOM:

    div[data-testid="stButtonGroup"]  (con role="radiogroup")
        └── button[role="radio"]      (uno por opción)
                └── atributo `data-selected` SOLO cuando está activo

Por eso todos los selectores que estilan un st.pills apuntan a
stButtonGroup / button[role="radio"] / [data-selected].
NO usar [data-testid="stPills"] ni `label` — no existen en este DOM.
Si Streamlit cambia el DOM en una actualización, verificar con DevTools
qué atributo marca el botón activo. Ojo: st.pills y st.segmented_control
rinden el MISMO DOM, así que cambiar uno por el otro no cambia nada
visualmente — si esperabas que sí, el estilo viene de una regla del
contenedor, no del widget.

Estructura del paquete (refactor 2026-08-01)
--------------------------------------------
El CSS vivia en un unico string de ~1600 lineas dentro de get_css().
Ahora cada seccion tiene su modulo y get_css() los concatena.

**El orden de _SECCIONES es parte del comportamiento**, no estetica: el
CSS usa !important en ambos lados de varios conflictos, asi que gana la
regla que aparece DESPUES. Por eso _99_movil va ultimo.

Para cambiar un estilo: ubica la seccion por el nombre del modulo y edita
ahi. Para agregar una: crea el modulo y sumalo a _SECCIONES en la posicion
correcta. Antes de estilar un widget nuevo lee la regla #6 de
arquitectura.md (acotar el selector a la key del widget, no al contenedor).
"""

import streamlit as st


# ===========================================================================
# MAPEO DE TAMAÑOS DE FUENTE
# ===========================================================================

TAM_FUENTE = {
    "Pequeño": 12,
    "Mediano": 14,
    "Grande": 17,
    "Muy grande": 20
}

from ._00_base import CSS as _CSS_BASE
from ._20_compras_rail import CSS as _CSS_COMPRAS_RAIL
from ._30_filtros import CSS as _CSS_FILTROS
from ._40_ajuste_franja import CSS as _CSS_AJUSTE_FRANJA
from ._50_fecha import CSS as _CSS_FECHA
from ._60_calendario import CSS as _CSS_CALENDARIO
from ._70_chrome import CSS as _CSS_CHROME
from ._80_cards import CSS as _CSS_CARDS
from ._90_franja_inferior import CSS as _CSS_FRANJA_INFERIOR
from ._99_movil import CSS as _CSS_MOVIL


# ORDEN SIGNIFICATIVO - ver el docstring. No reordenar a la ligera.
_SECCIONES = (
    _CSS_BASE,
    _CSS_COMPRAS_RAIL,
    _CSS_FILTROS,
    _CSS_AJUSTE_FRANJA,
    _CSS_FECHA,
    _CSS_CALENDARIO,
    _CSS_CHROME,
    _CSS_CARDS,
    _CSS_FRANJA_INFERIOR,
    _CSS_MOVIL,
)


def get_css():
    """Retorna el CSS completo como string.

    NO cachear con @st.cache_data: los _CSS_* son constantes importadas de
    submodulos; st.cache_data hashea el source de get_css y sus args (aca
    ninguno), pero no invalida cuando cambia el contenido de un submodulo
    editado. Resultado: en el preview las ediciones a estilos/_*.py quedan
    invisibles porque get_css devuelve el string cacheado del proceso
    anterior. El join de 11 strings es microsegundos; no vale la pena
    cachear a cambio de perder recarga en caliente.
    """
    return "\n" + "\n".join(_SECCIONES) + "\n    "


def inject_css():
    """Inyecta el CSS global en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
