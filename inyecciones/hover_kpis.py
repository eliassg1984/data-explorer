"""inyecciones.hover_kpis - unas cifras de resumen siguen al cursor.

DOS inyecciones, el mismo reparto de trabajo: los valores viajan con la
página y el intercambio pasa entero en el navegador.

  · `inject_hover_kpis`      — sobre un gráfico PLOTLY: las cifras resumen
                               el punto que tiene el cursor encima.
  · `inject_hover_kpis_grid` — sobre un AGGRID: cada grupo de cifras resume
                               una COLUMNA, y se enciende el de la columna
                               que tiene el cursor encima (2026-09-18, ver
                               arquitectura.md #460).

Lo que sigue describe la primera, que es la que estrenó el patrón; la
segunda tiene su propio docstring y repite sólo lo que cambia.

Un gráfico y, a su lado, cuatro cifras que resumen UN punto de ese gráfico.
En reposo resumen el último; con el cursor encima de un punto, ese. El caso
que lo estrenó es la tarjeta de Evolución de Compras › Proveedor
(`graficos/compras/proveedor.py`), pero nada acá sabe de proveedores: recibe
un contenedor y una tabla de valores ya formateados.

POR QUE JAVASCRIPT Y NO UN RERUN
    `st.plotly_chart(on_select=...)` reporta SELECCION (clic/lazo), no hover
    — el evento no existe del lado de Streamlit. Y aunque existiera: un rerun
    de esta app tarda 3-6s (por eso `estilos/_88_cargando.py` dibuja un velo),
    o sea que "seguir el cursor" a fuerza de servidor no es lento, es
    imposible. Asi que los valores de TODOS los puntos viajan con la pagina y
    el intercambio pasa entero en el navegador.

COMO SE ENGANCHA
    Plotly expone sus eventos en el propio div del grafico (`gd.on(...)`), no
    en el DOM, asi que hace falta JS de verdad: `inyectar_html` (un iframe con
    srcdoc), que es el unico camino en este proyecto — `st.markdown` deja
    muertos los `<script>` (arquitectura.md #7).

    El enganche se REINTENTA con un temporizador, igual que el scrollspy del
    rail (`graficos/base.py::_render_rail`) y por el mismo motivo: el div del
    grafico lo monta React cuando quiere, y en cada rerun puede reemplazarlo.
    El sello (`gd.__hoverKpis`) evita re-enganchar el mismo div dos veces, y
    `removeAllListeners` limpia el enganche VIEJO cuando React conserva el
    nodo y solo le cambia los datos — sin eso el listener anterior seguiria
    vivo con la tabla de valores de la corrida pasada.

TRAMPA MEDIDA
    `plotly_unhover` no siempre llega si el mouse sale rapido del grafico, y
    entonces las cifras se quedan congeladas en un periodo que ya no esta
    debajo del cursor — que es peor que no tener la funcion, porque no se nota.
    Por eso hay ademas un `mouseleave` sobre el div, que es el que garantiza
    la vuelta al valor de reposo.

Ver arquitectura.md regla #370.
"""

import hashlib
import json

from inyecciones._fragmentos import js_buscar_iframe
from inyecciones._iframe import inyectar_html


def inject_hover_kpis(clave_tarjeta, valores,
                      sel_grafico=".js-plotly-plot",
                      sel_titulo=".cp-evo-kpis-tit",
                      sel_valores=".cp-evo-kpis b"):
    """Engancha el hover del Plotly de `clave_tarjeta` a su pila de KPIs.

    · `clave_tarjeta` — la key del `st.container` que envuelve al gráfico Y a
      la pila. Se busca por `[class*="st-key-<clave>"]`, así que los dos
      selectores de abajo se resuelven DENTRO de esa tarjeta y no hace falta
      que sean únicos en la página.
    · `valores` — una entrada por punto del eje X, EN EL MISMO ORDEN que la
      traza: `{"tit": <encabezado>, "vals": [<cifra>, ...]}`, y opcionalmente
      `"cols": [<color CSS>, ...]` en el mismo orden (cadena vacía = el color
      que ya pone el CSS). Las cifras van ya formateadas (Python es el que
      sabe de monedas y decimales) y tienen que ser tantas como `<b>` dibuje
      la pila; si no coinciden, el JS no toca nada — prefiere quedarse quieto
      antes que escribir una cifra en la celda equivocada.

    El valor de REPOSO es el último de la lista: el mismo que Python acaba de
    dibujar. No se lee del DOM a propósito — leerlo obligaría a que el JS
    corriera después del render, y con el temporizador de enganche ese orden
    no está garantizado.
    """
    if not valores:
        return
    cuerpo = {"clave": clave_tarjeta, "filas": valores,
              "base": len(valores) - 1,
              "gr": sel_grafico, "tit": sel_titulo, "val": sel_valores}
    # El SELLO identifica esta tabla de valores, y es lo que decide si un div
    # ya enganchado hay que volver a engancharlo. No alcanza con "¿ya tiene
    # listener?": React reusa el nodo del gráfico entre reruns y le cambia
    # sólo los datos, así que un div viejo con listeners vivos seguiría
    # repartiendo las cifras de la corrida anterior. `md5` y no `hash()`
    # porque el built-in de Python está aleatorizado por proceso: serviría
    # igual acá (el sello sólo se compara consigo mismo dentro de una
    # pestaña), pero un valor que cambia entre corridas del server hace
    # imposible depurar por qué re-enganchó.
    cuerpo["sello"] = hashlib.md5(
        json.dumps(cuerpo, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    datos = json.dumps(cuerpo, ensure_ascii=False)
    inyectar_html(
        """<script>
        (function () {
          var w = window.parent, doc = w.document;
          var D = __DATOS__;
          var raiz = '[class*="st-key-' + D.clave + '"]';

          function pinta(i) {
            var f = D.filas[i];
            var cont = doc.querySelector(raiz);
            if (!f || !cont) return;
            var tit = cont.querySelector(D.tit);
            var bs  = cont.querySelectorAll(D.val);
            // Si la pila no tiene exactamente las celdas que esperamos, es
            // que el Python de al lado cambio y este JS quedo viejo: mejor
            // dejar las cifras que dibujo el servidor que repartir las
            // nuestras a ciegas.
            if (!tit || bs.length !== f.vals.length) return;
            tit.textContent = f.tit;
            for (var k = 0; k < bs.length; k++) {
              bs[k].textContent = f.vals[k];
              // El color de la celda, si la fila trae uno. Va INLINE y no
              // por clase porque asi lo escribe tambien el render de
              // Python: si el de reposo saliera de una clase, el primer
              // hover lo pisaria con un `style` y el `unhover` no podria
              // devolverlo (gana el inline). Cadena vacia = borrar el
              // inline y volver al color del CSS.
              if (f.cols) bs[k].style.color = f.cols[k] || '';
            }
            // Marca "esto NO es el valor de reposo": la usa el CSS para
            // tenir el encabezado mientras el cursor manda. Sin alguna senal,
            // cuatro cifras que cambian solas se leen como un parpadeo.
            tit.classList.toggle('cp-kpis-hover', i !== D.base);
          }

          if (w.__hoverKpisTimer) clearInterval(w.__hoverKpisTimer);
          w.__hoverKpisTimer = setInterval(function () {
            var cont = doc.querySelector(raiz);
            var gd = cont && cont.querySelector(D.gr);
            // `gd.on` solo existe cuando Plotly ya monto el grafico: un div
            // a medio construir se saltea y se reintenta al tick siguiente.
            if (!gd || !gd.on) return;
            if (gd.__hoverKpis === D.sello) return;
            gd.__hoverKpis = D.sello;
            if (gd.removeAllListeners) {
              gd.removeAllListeners('plotly_hover');
              gd.removeAllListeners('plotly_unhover');
            }
            gd.on('plotly_hover', function (ev) {
              var p = ev && ev.points && ev.points[0];
              if (!p) return;
              var i = (p.pointIndex != null) ? p.pointIndex : p.pointNumber;
              if (i != null) pinta(i);
            });
            gd.on('plotly_unhover', function () { pinta(D.base); });
            if (!gd.__hoverKpisSalida) {
              // Red de seguridad: ver "TRAMPA MEDIDA" en el docstring.
              gd.__hoverKpisSalida = true;
              gd.addEventListener('mouseleave', function () { pinta(D.base); });
            }
          }, 300);
        })();
        </script>""".replace("__DATOS__", datos))


def inject_hover_kpis_grid(clave_grid, clave_tarjeta, mapa,
                           reposo="docs", sel_tira=".sunat-kpis"):
    """Enciende el grupo de KPIs de la COLUMNA que tiene el cursor encima.

    Hermana de `inject_hover_kpis`, con el mismo reparto de trabajo (los
    valores viajan con la página, el intercambio pasa entero en el
    navegador) y la misma razón para existir: AG Grid no reporta hover del
    lado de Streamlit, y aunque lo hiciera, un rerun de esta app tarda 3-6s.

    · `clave_grid` — la `key=` del AgGrid. Se busca su iframe POR LA KEY
      (`js_buscar_iframe`, regla #455): esta página tiene siete grillas y
      «la primera con `.ag-root-wrapper`» es otra.
    · `clave_tarjeta` — la key del `st.container` donde vive la tira.
    · `mapa` — `{col-id: grupo}`. El `col-id` del DOM de AG Grid es el
      nombre del campo tal cual, así que el mapa se escribe con los mismos
      nombres de columna que el `GridOptionsBuilder`.
    · `reposo` — el grupo que queda encendido sin cursor encima.

    TRES COSAS QUE HAY QUE SABER SI SE TOCA ESTO

    **El listener va en el documento DEL IFRAME, delegado y en captura.**
    AG Grid virtualiza filas: engancharse a cada celda dejaría sin listener
    a todo lo que se dibuje al scrollear. Un solo `mouseover` en el
    documento y `closest('[col-id]')` sobre el target cubre celdas Y
    cabecera —las dos llevan `col-id`— y sobrevive a que AG Grid recicle
    los nodos.

    **La salida del grid la avisa el PADRE, no el iframe.** `mouseleave` no
    burbujea y dentro del iframe llega de forma poco fiable; el iframe
    ENTERO, visto desde el documento padre, sí emite un `mouseleave`
    limpio cuando el cursor se va. Misma trampa que documenta
    `inject_hover_kpis` para `plotly_unhover`: unos KPIs congelados en una
    columna que ya no está debajo del cursor son peores que no tener la
    función, porque no se nota.

    **El enganche se REINTENTA con un temporizador y lleva sello.** El
    iframe del componente se reemplaza en cada rerun, así que no alcanza
    con engancharse una vez; y el sello evita re-enganchar el mismo
    documento en cada tick.
    """
    if not mapa:
        return
    cuerpo = {"tarjeta": clave_tarjeta, "mapa": dict(mapa),
              "reposo": reposo, "tira": sel_tira}
    # Mismo criterio que `inject_hover_kpis`: `md5` y no `hash()`, que está
    # aleatorizado por proceso y haría imposible depurar un re-enganche.
    cuerpo["sello"] = hashlib.md5(
        json.dumps(cuerpo, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    datos = json.dumps(cuerpo, ensure_ascii=False)
    # LOS PARÉNTESIS NO SON DE ADORNO: sin ellos `.replace` se aplica sólo
    # al ÚLTIMO literal de la concatenación (precedencia de Python), y
    # `__DATOS__` vive en el PRIMERO. El script salía con
    # `var D = __DATOS__` tal cual: compila perfecto, revienta con un
    # ReferenceError dentro del iframe y la función no hace nada — sin
    # error en pantalla, sin nada en los logs del server. Se encontró
    # leyendo el `srcdoc` del iframe en el navegador. Ver regla #463.
    inyectar_html(("""<script>
    (function () {
      var w = window.parent, doc = w.document;
      var D = __DATOS__;
      """ + js_buscar_iframe(clave_grid) + """

      function activar(g) {
        var raiz = doc.querySelector(
            '[class*="st-key-' + D.tarjeta + '"] ' + D.tira);
        if (!raiz) return;
        var quiere = g || D.reposo;
        // `data-activo` no lo lee ningun CSS: queda en el DOM para que el
        // inspector del proyecto diga en que estado esta la tira.
        raiz.setAttribute('data-activo', quiere);
        var gs = raiz.querySelectorAll('.sunat-kpi-grupo');
        for (var i = 0; i < gs.length; i++) {
          gs[i].classList.toggle(
              'kpi-activo', gs[i].getAttribute('data-grupo') === quiere);
        }
      }

      if (w.__hoverKpisGridTimer) clearInterval(w.__hoverKpisGridTimer);
      w.__hoverKpisGridTimer = setInterval(function () {
        var f = buscarIframe();
        if (!f) return;
        var idoc = null;
        try { idoc = f.contentDocument; } catch (e) { return; }
        if (!idoc || !idoc.body) return;
        if (idoc.__hoverKpisGrid !== D.sello) {
          idoc.__hoverKpisGrid = D.sello;
          idoc.addEventListener('mouseover', function (ev) {
            var t = ev.target;
            var el = (t && t.closest) ? t.closest('[col-id]') : null;
            var id = el ? el.getAttribute('col-id') : null;
            // Una columna sin grupo (Fecha, D) deja la tira en reposo: es
            // mejor no decir nada que encender un grupo que no la resume.
            activar((id && D.mapa[id]) ? D.mapa[id] : null);
          }, true);
        }
        if (!f.__hoverKpisGridSalida) {
          f.__hoverKpisGridSalida = true;
          f.addEventListener('mouseleave', function () { activar(null); });
        }
      }, 300);
    })();
    </script>""").replace("__DATOS__", datos))
