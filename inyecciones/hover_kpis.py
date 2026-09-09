"""inyecciones.hover_kpis - la pila de KPIs sigue al cursor sobre un Plotly.

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
      traza: `{"tit": <encabezado>, "vals": [<cifra>, ...]}`. Las cifras van
      ya formateadas (Python es el que sabe de monedas y decimales) y tienen
      que ser tantas como `<b>` dibuje la pila; si no coinciden, el JS no
      toca nada — prefiere quedarse quieto antes que escribir una cifra en
      la celda equivocada.

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
            for (var k = 0; k < bs.length; k++) bs[k].textContent = f.vals[k];
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
