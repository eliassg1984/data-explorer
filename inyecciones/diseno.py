"""inyecciones.diseno - modo de diseño visual (herramienta de desarrollo).

Deja fijar un elemento (mismo Fijar del inspector) y previsualizar cambios
de estilo en vivo sobre el DOM real — nunca persiste en estilos/ ni en
session_state. Activación: `?debug=1&diseno=1` juntos en la URL (releído en
cada tick, no una sola vez al cargar).

Acoplamiento con inspector.py (Regla viva, arquitectura.md #4 y #46): este
módulo LEE `win.__inspectorPinned` / `win.__inspectorUltimo`, que
`inyecciones/inspector.py` ya expone en `window.parent` para sobrevivir el
remount del iframe en cada rerun. Es una dependencia de solo lectura —
`inspector.py` no importa ni llama nada de este módulo, así que la regla
"ninguna función depende de otra" del paquete sigue valiendo en el sentido
de invocación directa; lo que se documenta acá es el contrato de datos
compartido (nombres de esas dos variables + la forma de `elemento.key`).
Si `inspector.py` alguna vez renombra esas variables o cambia qué guarda
`__inspectorUltimo`, este módulo se rompe — avisar en ambos lados.

El elemento pineado se re-resuelve por key en CADA ejecución del script
(nunca se confía en la referencia DOM capturada al momento del pin): un
rerun real preserva el nodo gracias a la reconciliación por key de
Streamlit, pero el propio iframe de este `components.html` se destruye y
recrea igual que el de `inspector.py`, así que los listeners/loops sí deben
reinstalarse cada vez (mismo patrón remove-old/add-new).

Fase A.2 agrega los controles de caja/geometría: manijas de resize/mover
sobre el overlay, y radio de borde / padding / borde completo / sombra /
"ver original" en el panel. Todo se aplica con
`elemento.style.setProperty(prop, valor, 'important')` y se trackea en
`win.__disenoState.porKey[key]` para poder reaplicarlo defensivamente en
cada ejecución del script (arquitectura.md #46: los estilos inline
sobreviven un rerun real, pero el iframe/listeners no).

Fase B agrega tipografía (tamaño, peso, alineación, subrayado, espaciado
entre letras, rotar) y color por rol (texto / fondo / borde, tres filas de
swatches independientes — nunca un acento único). Primer uso de datos
Python reales en este módulo: la paleta se importa de `tema.py` y se
serializa al script igual que `_mapas_desarrollador()` en inspector.py
(`json.dumps` + placeholder), para no hardcodear hex sueltos (CLAUDE.md
"nunca un #hex suelto").

Fase C agrega INSERTAR: elementos de mentira ("mocks") para ver cómo se
vería algo que todavía no existe — Texto (editable en el lugar), Línea,
Barra y Espacio, anclados antes/dentro/después del elemento pineado. Nacen
con la clase `st-key-<key>`, así que se fijan con clic derecho como
cualquier widget y heredan todos los controles de arriba sin código extra.
No existen para React: `reponerMocks()` (en cada tick de `sync()`, antes de
resolver el pin) los vuelve a insertar cuando Streamlit re-renderiza esa
rama, con sus cambios de estilo reaplicados. Nunca persisten: no están en
el código ni en `estilos/` y mueren al recargar — el panel lo avisa.
Detalle en arquitectura.md regla #151.

El pin baja a un hijo SIN key propia (sub-pin, arquitectura.md #157): el
inspector ancla siempre al contenedor con `st-key-*` mas cercano, asi que
un titulo de `st.markdown` (`<div class="cp-rank-tit">`) pineaba la TARJETA
y "Mover" corria los 929x388 px del contenedor sin mover el titulo adentro.
El arbol de jerarquia suma hojas con las clases DE AUTOR de los hijos (las
que escribe este proyecto; se filtran `st-*`, `st[A-Z]`, `ag-*`, los hashes
sin prefijo de emotion tipo `e1rw0b1u1` y todo lo que viva dentro de otro
`st-key-`): un clic baja el pin ahi, un clic en la fila de la key lo sube.
Se guarda la CLASE, nunca el nodo, y el indice de
`win.__disenoState.porKey` pasa a ser el `id` (`key .clase`), no la key —
la tarjeta y cada hijo llevan cambios independientes. `construirBloqueCSS`
y los mocks siguen el sub hasta el final: el CSS copiado sale anclado a
`div[class*="st-key-K"] .cp-rank-tit` y `anclaSub` inserta el mock pegado
al hijo, no a la tarjeta.

El panel se puede colapsar a una pill chica (botón "–" en su cabecera,
click en la pill para expandir, o Alt+D) — pensado para el caso "el panel
ocupa lugar aunque no haya nada que ajustar todavía". Colapsar/expandir es
una preferencia de sesión (`win.__disenoState.panelColapsado`), no depende
de la key pineada; el overlay y las manijas del elemento pineado siguen
funcionando igual con el panel colapsado.

Los controles de ESTILO (todo salvo tamaño/posición/flex — ver
PROPS_GEOMETRIA) no escriben siempre sobre `elemento`: `destinosDeEstilo()`
redirige a los `<button>` de adentro cuando el elemento pineado ES
básicamente un botón/pill (st.pills, segmented_control, un st.button o
st.popover sueltos) — esos widgets guardan la key en un wrapper de layout
sin ningún borde/relleno/tipografía propios; lo visualmente real vive en
el/los botones, que no tienen key. Dos cortes, en este orden:
CANTIDAD primero (varios botones SUELTOS, fuera de un `stButtonGroup`, =
lista de botones — el rail, no un botón) y recién después ÁREA (>=60% del
ancho o alto del elemento), que descarta la tarjeta grande con flechitas ▸
salpicadas por sus filas. El corte por cantidad no es redundante: la suma
de anchos de una COLUMNA de botones supera siempre al contenedor, así que
el área sola daba verdadero en cualquier rail (ver arquitectura.md #48).
Cuando la redirección SÍ aplica, el panel lo dice en una línea arriba de
los controles — el contorno violeta marca el elemento pineado y no puede
marcar dos cosas a la vez.
`width`/`height`/`flex`/`max-width`/`max-height` siempre van al elemento
mismo, para que coincida con lo que trackean el overlay y las manijas.

`neutralizarTransicion()` (arquitectura.md #48) corta `transition` con
`!important` antes de tocar cualquier propiedad animable — un botón con
`transition: all 0.15s` puede quedar con la propiedad SIN aplicar, con el
inline `!important` confirmado presente y todo, porque el setInterval de
150ms de `sync()` reinicia la transición en cada tick casi a la par de su
propia duración y nunca llega a destino. No tira error: se ve como "mi
cambio no hizo nada".
"""

import json

import streamlit.components.v1 as components

from inyecciones._diseno_js import JS
from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO_OSCURO, LAVANDA_FONDO,
    EXITO, ADVERTENCIA, ERROR,
    AJUSTE_POS, AJUSTE_NEG,
    TEXTO_PRINCIPAL, GRIS_TEXTO, GRIS_TEXTO_SUAVE, BLANCO,
    GRIS_FONDO, GRIS_BORDE, GRIS_LINEA,
)

# Dos familias, a propósito separadas: DATO (acento + semáforo + ajuste) es
# lo que ya traía la paleta desde la fase B; SUPERFICIE (grises + lavanda
# tenue) se agregó el 2026-08-21 porque faltaba justo lo que más se prueba
# en Fondo/Borde — probar "¿este gris de tarjeta, o el lienzo?" no se podía
# hacer sin ella (ver arquitectura.md regla #153).
_PALETA = [
    {"hex": ACENTO, "nombre": "Acento"},
    {"hex": ACENTO_FUERTE, "nombre": "Acento fuerte"},
    {"hex": ACENTO_TEXTO_OSCURO, "nombre": "Indigo oscuro"},
    {"hex": EXITO, "nombre": "Exito"},
    {"hex": ADVERTENCIA, "nombre": "Advertencia"},
    {"hex": ERROR, "nombre": "Error"},
    {"hex": AJUSTE_POS, "nombre": "Ajuste positivo"},
    {"hex": AJUSTE_NEG, "nombre": "Ajuste negativo"},
    {"hex": TEXTO_PRINCIPAL, "nombre": "Texto principal"},
    {"hex": BLANCO, "nombre": "Blanco"},
    {"hex": GRIS_FONDO, "nombre": "Gris lienzo"},
    {"hex": GRIS_BORDE, "nombre": "Gris borde"},
    {"hex": GRIS_LINEA, "nombre": "Gris linea"},
    {"hex": GRIS_TEXTO, "nombre": "Gris texto"},
    {"hex": GRIS_TEXTO_SUAVE, "nombre": "Gris texto suave"},
    {"hex": LAVANDA_FONDO, "nombre": "Lavanda tenue"},
]


def inject_diseno_visual():
    """Inyecta el modo de diseno visual. El JS vive en _diseno_js.py
    (794 lineas); aca solo queda la sustitucion de la paleta."""
    components.html(JS.replace("__PALETA__", json.dumps(_PALETA)),
                    height=0, scrolling=False)
