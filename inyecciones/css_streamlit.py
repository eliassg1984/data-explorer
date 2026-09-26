"""inyecciones.css_streamlit - le quita a Streamlit las `:has()` que traban la página.

Regla #532. La #469 prohíbe en NUESTRO CSS un atributo o una pseudo-clase
de estado adentro de un `:has()`: con una sola de esas en la página, cada
cambio del DOM recalcula los estilos de la página entera. El test
`_pruebas_has_solo_clases` lo vigila... sobre `estilos/`, `graficos/` y
`tablas/`. El CSS del propio Streamlit no lo mira nadie, y trae dos:

    .st-emotion-cache-…:not([data-selected]):not([data-disabled])
        :has(+ button[data-variant="segmented_control"][data-selected]…)
    …:has(+ button[data-variant="segmented_control"]…
        :is([data-hovered], [data-focus-visible]))

Son el separador de `st.segmented_control`: le borran el filo derecho al
botón que queda a la izquierda del elegido o del que tiene el cursor.
Emotion las inserta con el primer selector segmentado de la sesión y no las
saca nunca, y la app usa ese widget en ~30 sitios.

MEDIDO el 2026-09-25 en Compras, 1366×768, datos reales:

    cambio                                    con ellas   sin ellas
    insertar un elemento en una sección       115-138 ms   0,1-0,3 ms
    `data-hovered` en un botón (hover)          114 ms      0,1 ms
    cambiar la granularidad (gesto real)        1,1 s       0,8 s  bloqueado

Las 160 `:has()` que había en la página, medidas de a una, suman 19 ms: el
costo no es de ellas sino de ESTAS dos, y hace falta sacar las DOS (con
cualquiera de las dos sola el recálculo sigue siendo de la página entera).
Y el `data-hovered` lo escriben, en la 1.64 de Cloud, los desplegables, las
casillas, los inputs, los sliders, las fechas, los radios y los
multiselect: pasar el cursor por cualquier control costaba 114 ms, y al
hacer scroll con el mouse quieto el navegador actualiza el hover de lo que
pasa por debajo.

CÓMO. No hay CSS que desactive un selector: el costo es que EXISTA. Así que
se borran del sheet de emotion (`<style data-emotion>`, que en producción
se llena con `insertRule` y no con texto), en dos tiempos:

  · al cargar, lo que ya está;
  · después, envolviendo `CSSStyleSheet.prototype.insertRule` del
    documento de la app: la regla entra y, si es de emotion y es cara, sale
    en la misma tarea — el navegador nunca llega a recalcular con ella.
    Emotion inserta siempre al final y no mira el índice que devuelve, así
    que sacarla no le desordena nada.

Sólo se tocan hojas de emotion, y sólo reglas con un ATRIBUTO, un `:hover`
o un `:active` adentro de un `:has()`: lo que cambia con el puntero.
Barridos los bundles de la 1.59 (local) y la 1.64 (Cloud), eso es:

    st.segmented_control   las dos de arriba              (1.59 y 1.64)
    st.multiselect         `:not(:has([data-focused]))…` resalta la
                           primera opción de la lista abierta   (1.64)
    un componente de pasos `[data-step]:has(+ [data-step])`     (1.64)

Se QUEDAN las de foco (`:focus-within:has(:focus-visible)` del deslizador,
la tabla y el error): el foco cambia al tabular, no al mover el mouse, y
estaban en la página cuando se midieron los 0,1 ms. Y las que llevan
clases o etiquetas (`:has(> .stCacheSpinner)`, `:has(pre)`…), que no
cuestan. El criterio vive UNA vez, en `_CARO`, y el script lo recibe
escrito; `es_has_caro` es la misma cuenta en Python, para los tests.

Lo que se pierde a la vista: en el segmentado, un filo gris de 1px al lado
de la opción elegida; en el multiselect, el resaltado de la primera opción
mientras nadie pasó por la lista.

Módulo NUEVO a propósito, y `app.py` lo importa por su ruta y no desde el
paquete: en Cloud el paquete `inyecciones` ya cargado es el VIEJO, y pedirle
un nombre que no tiene tira la app hasta que alguien la reinicia (regla
#357). Un submódulo que no estaba se carga fresco del disco.
"""

import json
import re

from inyecciones._iframe import inyectar_html

# Las pseudo-clases que cambian con cada movimiento del puntero. Las de foco
# NO: cambian al tabular, y la del deslizador estaba en la página medida.
_PSEUDOS_DEL_PUNTERO = ("hover", "active")

# Un atributo, o una de esas pseudo-clases, en el argumento de un `:has()`.
# La misma expresión corre en Python (`es_has_caro`) y en JS (el script).
_CARO = r"\[|:(?:%s)(?![\w-])" % "|".join(_PSEUDOS_DEL_PUNTERO)


def es_has_caro(selector: str) -> bool:
    """¿Algún `:has()` de `selector` lleva adentro un atributo o un estado?

    Misma cuenta que `esCaro` del script de abajo, paréntesis balanceados
    incluidos: un `[data-x]` DESPUÉS del `:has()` no cuenta, porque no le
    cambia el costo."""
    i = 0
    while (i := selector.find(":has(", i)) != -1:
        j, prof = i + 5, 1
        while j < len(selector) and prof:
            prof += (selector[j] == "(") - (selector[j] == ")")
            j += 1
        if re.search(_CARO, selector[i + 5:j - 1]):
            return True
        i = j
    return False


_SCRIPT = """<script>
(function () {
  var w = window.parent, doc = w.document;
  var CARO = new RegExp(__CARO__);

  function esCaro(sel) {
    var i = 0;
    while ((i = sel.indexOf(':has(', i)) !== -1) {
      var j = i + 5, prof = 1;
      while (j < sel.length && prof) {
        var c = sel.charAt(j);
        if (c === '(') prof++; else if (c === ')') prof--;
        j++;
      }
      if (CARO.test(sel.slice(i + 5, j - 1))) return true;
      i = j;
    }
    return false;
  }
  function deEmotion(hoja) {
    var n = hoja && hoja.ownerNode;
    return !!(n && n.hasAttribute && n.hasAttribute('data-emotion'));
  }
  // Recorre de atrás para adelante: borrar no corre los índices pendientes.
  function limpiar(reglas, dueno) {
    var n = 0;
    for (var i = reglas.length - 1; i >= 0; i--) {
      var r = reglas[i];
      if (r.cssRules && !r.selectorText) { n += limpiar(r.cssRules, r); continue; }
      if (r.selectorText && r.selectorText.indexOf(':has(') !== -1
          && esCaro(r.selectorText)) {
        if (w.__hasCaroEjemplos.length < 8) w.__hasCaroEjemplos.push(r.selectorText);
        dueno.deleteRule(i);
        n++;
      }
    }
    return n;
  }

  w.__hasCaroQuitadas = w.__hasCaroQuitadas || 0;
  w.__hasCaroEjemplos = w.__hasCaroEjemplos || [];

  // 1) Lo que emotion ya insertó antes de que cargara este iframe.
  var hojas = doc.querySelectorAll('style[data-emotion]');
  for (var k = 0; k < hojas.length; k++) {
    try { w.__hasCaroQuitadas += limpiar(hojas[k].sheet.cssRules, hojas[k].sheet); }
    catch (e) {}
  }

  // 2) Lo que inserte después: entra y sale en la misma tarea. Una sola
  // envoltura por documento aunque este iframe se vuelva a cargar.
  var P = w.CSSStyleSheet.prototype;
  if (!P.insertRule.__sinHasCaro) {
    var original = P.insertRule;
    var envuelta = function (regla) {
      var i = original.apply(this, arguments);
      try {
        if (deEmotion(this) && String(regla).indexOf(':has(') !== -1) {
          var r = this.cssRules[i];
          if (r && r.cssRules && !r.selectorText) {
            w.__hasCaroQuitadas += limpiar(r.cssRules, r);
          } else if (r && r.selectorText && esCaro(r.selectorText)) {
            if (w.__hasCaroEjemplos.length < 8) w.__hasCaroEjemplos.push(r.selectorText);
            this.deleteRule(i);
            w.__hasCaroQuitadas++;
          }
        }
      } catch (e) {}
      return i;
    };
    envuelta.__sinHasCaro = true;
    P.insertRule = envuelta;
  }
})();
</script>"""


def neutralizar_has_streamlit() -> None:
    """Saca del documento las `:has()` caras del CSS de Streamlit (regla #532).

    Va en cada corrida, como el resto de las inyecciones: el iframe no se
    recarga si su HTML no cambia, así que en la práctica el script corre
    una vez por página. `window.parent.__hasCaroQuitadas` dice cuántas
    reglas sacó y `__hasCaroEjemplos`, cuáles — para mirarlo desde la
    consola en Cloud."""
    inyectar_html(_SCRIPT.replace("__CARO__", json.dumps(_CARO)))
