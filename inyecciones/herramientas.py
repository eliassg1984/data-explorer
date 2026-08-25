"""inyecciones.herramientas - barra unificada de herramientas de desarrollo.

Un solo lugar para prender/apagar TODAS las herramientas de diagnostico, en
vez de tres URLs distintas y dos scripts que habia que pegar a mano en la
consola de DevTools. Activacion: `?debug=1` (el mismo flag que ya encendia
el inspector; no hay flag nuevo que recordar).

    🔍 Inspector   tooltip con selectores/archivo:linea/estilos
    🎨 Diseno      editar en vivo el elemento fijado
    🩻 Rayos X     pinta la estructura (flujo / escapados / pseudo-elementos)
    📐 Layout      auditor de contenedores, con panel en la app
    📊 Graficos    auditor de textos pisados/cortados, con panel en la app

Los modos son COMBINABLES a proposito (Rayos X + Inspector es justo la
combinacion util: ves la estructura pintada Y podes hover para el detalle).
Cuando dos se estorban, la barra lo AVISA en vez de bloquearlos — hoy el
unico par asi es Diseno + Rayos X, porque Diseno mueve con `transform` y eso
captura a los hijos `fixed`, asi que los recuadros salen corridos
(arquitectura.md regla #156).

UNA SOLA FUENTE PARA LOS AUDITORES
Los tres auditores NO se reimplementan aca: este modulo LEE los ficheros de
`herramientas/*.js` y los embebe en el script. Son los mismos que se siguen
pudiendo pegar en la consola — dos formas de correr el mismo codigo, sin dos
copias que se desincronicen (el riesgo real: `auditar_layout.js` ya cambio
cuatro veces desde que se escribio). Si se agrega un auditor nuevo, va a
`_FUENTES` y a `MODOS`/`ACCIONES` en `_herramientas_js.py`.

Se ejecutan inyectando un `<script>` en el documento del PADRE, no en el
iframe de este `inyectar_html`: estan escritos para la consola y usan
`document`/`window` directo, asi que corriendolos aca mirarian el DOM del
iframe (vacio). Con el `<script>` en el padre quedan definidos sobre la app
real, y de paso siguen disponibles para llamarlos a mano desde la consola
sin pegar nada.

ACOPLAMIENTO CON inspector.py (Regla viva, arquitectura.md #4)
Dos contratos, los dos de solo lectura hacia inspector.py — que no sabe que
este modulo existe:

1. El boton "Inspector" de la barra NO toca `?debug=1` (ese flag es el que
   hace visible a la barra: apagarlo la haria desaparecer a ella tambien).
   Alterna el silenciador que inspector.py ya expone en `window.parent`:
   `__inspectorTooltipSilenciado` (lectura) y `__inspectorAlternarSilenciado`
   (invocacion). Si inspector.py renombra esos dos, el boton deja de
   funcionar — avisar en ambos lados.
2. ESPACIO COMPARTIDO: la barra vive en `bottom:10px; left:72px`, que es
   donde estaba el badge "Inspector ON" de inspector.py. Ese badge se corrio
   a `bottom:46px` para apilarse ENCIMA de la barra; el comentario esta
   tambien en `_inspector_js.py`, junto a su `cssText`.

El Alt+I del inspector reescribe la URL con `replaceState`, que no dispara
`popstate`: la barra instala su propio listener de Alt+I para no quedarse
colgada en pantalla despues de salir con el atajo.
"""

import json
from pathlib import Path

from inyecciones._herramientas_js import JS
from inyecciones._iframe import inyectar_html

# nombre en el script  ->  fichero en herramientas/
_FUENTES = {
    "rayos_x": "rayos_x.js",
    "auditar_layout": "auditar_layout.js",
    "auditar_graficos": "auditar_graficos.js",
}

_DIR_HERRAMIENTAS = Path(__file__).resolve().parent.parent / "herramientas"


def _leer_fuentes():
    """Lee los .js de herramientas/. Un fichero que falte se omite en vez de
    reventar la app: la barra lo reporta cuando se clickea ese boton, que es
    mucho mejor que dejar el reporte sin dibujar por una herramienta de
    desarrollo."""
    fuentes = {}
    for nombre, fichero in _FUENTES.items():
        ruta = _DIR_HERRAMIENTAS / fichero
        try:
            fuentes[nombre] = ruta.read_text(encoding="utf-8")
        except OSError:
            continue
    return fuentes


def inject_herramientas():
    """Inyecta la barra unificada. Sin ?debug=1 el script sale a las tres
    lineas y no carga ninguna fuente: coste cero en produccion."""
    # El </script> de un fichero embebido cerraria el <script> que lo
    # contiene aunque este dentro de un string JS. Ninguno de los tres lo
    # tiene hoy, pero el escape va igual: el dia que alguien meta uno en un
    # comentario, el sintoma seria la barra entera rota sin causa visible.
    fuentes = json.dumps(_leer_fuentes()).replace("</", "<\\/")
    inyectar_html(JS.replace("__FUENTES__", fuentes), height=0)
