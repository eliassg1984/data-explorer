"""inyecciones._iframe - el primitivo bajo TODAS las inyecciones.

Cada `inject_*` de este paquete hace lo mismo: meter un `<script>` dentro de
un iframe con `srcdoc` para que CORRA de verdad. `st.markdown` no sirve:
inserta el HTML por innerHTML y el HTML spec deja muertos los `<script>` que
vengan ahi (arquitectura.md #7). El iframe es el unico camino.

Ese iframe lo daba `st.components.v1.html`, que Streamlit DEPRECO con fecha
de retiro **2026-06-01 — ya pasada**. Como `requirements.txt` pide
`streamlit>=1.39,<2`, Streamlit Cloud puede resolver en cualquier deploy una
version donde la funcion ya no exista: no es un warning molesto, es la app
entera reventando en los 12 puntos donde se llama. De ahi este modulo.

Ver arquitectura.md #204 para el detalle de la migracion.
"""

import streamlit as st

# `st.iframe` es el reemplazo oficial, pero no existe en toda la banda que
# admite requirements.txt (llego mucho despues de 1.39). Se resuelve UNA vez,
# al importar: es una capacidad del interprete, no algo que cambie por rerun.
_HAY_ST_IFRAME = hasattr(st, "iframe")

# `st.iframe` RECHAZA height<=0 (`validate_height` -> StreamlitInvalidHeightError),
# y las 11 inyecciones invisibles pasaban justamente `height=0`. Se les da el
# minimo legal; quien las hace invisibles de verdad es el CSS, no este numero
# — ver `inyectar_html`.
_ALTO_MINIMO = 1


def inyectar_html(html: str, height: int = 0) -> None:
    """Ejecuta `html` (en la práctica, un `<script>`) dentro de un iframe.

    Reemplazo directo de `components.html(html, height=..., scrolling=...)`.

    `height=0` (el default) significa "inyección invisible": la inyección no
    dibuja nada, sólo alcanza `window.parent` para tocar el documento de la
    app. Es el caso de 11 de los 12 call sites; el único visible es el panel
    de rendimiento de `perf.py`, con `height=300`.

    TRES cosas que hay que saber antes de tocar esto:

    · **`st.iframe` SÍ acepta una string de HTML.** No hace falta ni fichero
      temporal ni `data:` URL. Su cascada de tipos es Path → URL absoluta →
      fichero existente → URL relativa (`/…`) → **string de HTML**, y el
      último caso escribe `srcdoc`, exactamente el mismo campo del mismo
      proto que escribía `components.html`. Además `_is_file()` corta de una
      si la string trae `<`, así que un blob de JS nunca se confunde con una
      ruta. Consecuencia importante: para el frontend los dos caminos son
      INDISTINGUIBLES, así que `window.parent` sigue alcanzando el documento
      padre igual que siempre (mismo origen, mismo anidado) y la regla #39
      —en Cloud la app ya vive dentro de un iframe y éste agrega un segundo
      nivel— no cambia ni para mejor ni para peor.

    · **El `height=0` nunca fue lo que escondía estos iframes.** Los esconde
      el CSS: `estilos/_00_base.py` fuerza `[data-testid="stIFrame"]` a
      `height: 0 !important` y `navegacion.py` le pone `display: none` al
      `stElementContainer` que lo envuelve (para matar el gap del bloque
      vertical). Por eso subir el alto a 1px acá no se ve: el `!important`
      del CSS gana igual. El 0 de la firma se conserva porque documenta la
      INTENCIÓN en los call sites.

    · **`scrolling` ya no existe.** `st.iframe` fija `scrolling = True` en el
      proto y no lo expone. Daba igual: un iframe de 0px con `overflow:
      hidden` en el wrapper no puede mostrar una barra.
    """
    if _HAY_ST_IFRAME:
        st.iframe(html, height=height if height > 0 else _ALTO_MINIMO)
        return
    # Streamlit viejo (< st.iframe). El import va acá adentro a propósito: en
    # una versión moderna no queremos ni tocar el módulo deprecado.
    import streamlit.components.v1 as components
    components.html(html, height=height, scrolling=False)
