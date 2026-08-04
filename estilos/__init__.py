"""
Estilos globales de la app: CSS, tamaños de fuente e inyección del tema.

ÍNDICE (buscar el header exacto con Ctrl+F)
-------------------------------------------
    L  112  PALETA DE COLORES — variables :root del tema CallAI
    L  170  HEADER NATIVO + ESPACIO SUPERIOR
    L  197  IFRAMES INVISIBLES (por defecto)
    L  211  PANEL DE RENDIMIENTO DEL NAVEGADOR (excepción iframe)
    L  225  BOTÓN PARA EXPANDIR EL SIDEBAR
    L  234  ESTILOS BASE — tipografía, fondos, layout raíz
    L  274  INPUTS Y BOTONES
    L  313  EXPANDER
    L  328  CAPTION Y ALERTAS
    L  354  SIDEBAR NAV
    L  373  AGGRID — ancho completo
    L  383  CONTROL DE TAMAÑO EN SIDEBAR
    L  389  MÓVIL — LAYOUT GENERAL
    L  469  SELECTOR DE VISTA (Tabla / Gráficos) — pestañas ghost
    L  565  PESTAÑAS DE TIPO DE GRÁFICO (fila pegada al tope del gráfico)
    L  606  BOTÓN FILTROS (popover)
    L  624  FILA SUPERIOR DE AJUSTE DE INVENTARIO — franja blanca sticky
    L  684  CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / etc.
    L  793  FECHA EN EL HEADER — trigger del popover (atajos + calendario)
    L  866  CALENDARIO DESPLEGABLE (BaseWeb)
    L  887  OCULTAR TOOLBARS NATIVAS DE STREAMLIT
    L  907  POSICIÓN DEL TOAST (st.toast)
    L  917  AVISO DE REFRESCO EN CURSO
    L  930  CARDS DE GRÁFICOS — contenedor blanco (ajuste_graf_card_*)
    L 1043  TARJETAS DEL DRILL DE PROVEEDOR (compras_prov_card_*)
    L 1074  FRANJA INFERIOR FIJA — cierre visual del área de contenido
    L 1129  MÓVIL — overrides @media (SIEMPRE al final; no mover)

Al mover secciones, ACTUALIZAR estos números. Los @media al final NO se
tocan de posición: van al fondo para que ninguna regla desktop las pise.

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

Excepciones conocidas (widgets estilados por su propia key, legado):
- `[class*="st-key-vistatabs_"]` — pestañas Tabla/Gráficos (bloque L 426).
  A consolidar la próxima vez que se toque ese bloque.

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

Por eso todos los selectores del "selector de vista" apuntan a
stButtonGroup / button[role="radio"] / [data-selected].
NO usar [data-testid="stPills"] ni `label` — no existen en este DOM.
Si Streamlit cambia el DOM en una actualización, verificar con DevTools
qué atributo marca el botón activo y actualizar SOLO el bloque
"SELECTOR DE VISTA" (hay uno único, buscar ese título).

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
from ._10_vista import CSS as _CSS_VISTA
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
    _CSS_VISTA,
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
    """Retorna el CSS completo como string (cacheado para no reinyectar)."""
    # El envoltorio ('\n' inicial y '\n    ' final) reproduce exactamente el
    # string literal que devolvia la version de un solo bloque.
    return "\n" + "\n".join(_SECCIONES) + "\n    "


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
