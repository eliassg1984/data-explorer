"""inyecciones.varios - inyecciones sueltas de chrome de la app.

Overlay de errores, modo pantalla completa, alineacion de la cabecera de
Ajuste, footer de ultima actualizacion y traduccion del calendario.
"""

import json
from inyecciones._iframe import inyectar_html


def inject_error_overlay():
    """Captura los errores de JavaScript de la ventana principal y los muestra
    en un panel rojo fijo en pantalla. Asi los errores quedan VISIBLES (tambien
    en capturas de pantalla), sin necesidad de abrir la consola del navegador.

    Mejoras:
    - Filtra el ruido de las EXTENSIONES del navegador (content.js,
      chrome-extension, giveFreely, etc.) para que solo veas errores de TU app.
    - Solo texto ASCII (sin emojis) para no romper el propio script.
    - Cada error muestra de donde viene, para ubicarlo mas facil.

    Otros scripts inyectados pueden reportar manualmente con:
        window.__logErr('mi mensaje')
    """
    inyectar_html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      if (win.__errOverlayInit) return;
      win.__errOverlayInit = true;
      win.__errLog = [];

      // Origenes que NO son de tu app (extensiones del navegador). Sus errores
      // se ignoran para que el panel quede limpio.
      function esRuidoExterno(texto){
        var t = String(texto || '').toLowerCase();
        return (t.indexOf('content.js') !== -1
             || t.indexOf('chrome-extension') !== -1
             || t.indexOf('givefreely') !== -1
             || t.indexOf('receiving end does not exist') !== -1
             || t.indexOf('extension context') !== -1);
      }

      function render(){
        var box = doc.getElementById('err-overlay');
        if (!win.__errLog.length){ if (box) box.remove(); return; }
        if (!box){
          box = doc.createElement('div');
          box.id = 'err-overlay';
          // #7f1d1d: rojo oscuro del overlay de ERRORES (herramienta interna
          // de depuracion, no interfaz de usuario). Excepcion intencional.
          box.style.cssText = 'position:fixed;bottom:8px;right:8px;max-width:540px;'
            + 'max-height:42vh;overflow:auto;z-index:2147483647;background:#7f1d1d;'
            + 'color:#fff;font:12px/1.45 monospace;padding:10px 12px;border-radius:8px;'
            + 'box-shadow:0 4px 16px rgba(0,0,0,.4)';
          doc.body.appendChild(box);
        }
        var items = win.__errLog.slice(-12).map(function(e){
          return String(e).replace(/&/g,'&amp;').replace(/</g,'&lt;');
        }).join('<br>--<br>');
        box.innerHTML = '<b>Errores JS de tu app (' + win.__errLog.length + ')</b>'
          + '<span style="float:right;cursor:pointer;opacity:.7" '
          + 'onclick="this.parentNode.remove()">[x]</span><br>' + items;
      }

      function log(m){
        if (esRuidoExterno(m)) return;
        win.__errLog.push(String(m).slice(0,400));
        render();
      }

      win.addEventListener('error', function(ev){
        var origen = ev.filename || '';
        if (esRuidoExterno(origen)) return;
        log('[error] ' + (ev.message || ev.error) + (origen ? ' @ ' + origen : ''));
      });
      win.addEventListener('unhandledrejection', function(ev){
        var msg = (ev.reason && ev.reason.message) || ev.reason;
        log('[promise] ' + msg);
      });
      win.__logErr = log;
      win.__errRender = render;
    })();
    </script>
    """, height=0)
def inject_fullscreen_app():
    """Botón flotante ⛶ que pone TODA la webapp en pantalla completa — el
    equivalente web de F11 (Fullscreen API sobre document.documentElement).
    Un toque entra, otro toque o Esc sale. Solo visible en móvil (en desktop ya
    está F11 del teclado). Android y desktop lo soportan; iPhone Safari NO
    (limitación de Apple) → ahí no hay efecto. Mismo patrón que
    inject_maximize_aggrid, pero sobre el documento padre completo en vez del
    iframe de la tabla: el botón vive en el padre y su onclick pide fullscreen
    del documentElement (la activación de usuario del clic es válida)."""
    inyectar_html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var BTN = 'app-fs-btn', STY = 'app-fs-style', tries = 0, MAX = 40;
      function fsOn(){ return doc.fullscreenElement || doc.webkitFullscreenElement || null; }
      function toggle(){
        if (fsOn()){
          var ex = doc.exitFullscreen || doc.webkitExitFullscreen;
          if (ex) ex.call(doc);
          return;
        }
        var el = doc.documentElement;
        var req = el.requestFullscreen || el.webkitRequestFullscreen;
        if (req) req.call(el);
      }
      function ensureStyle(){
        if (doc.getElementById(STY)) return;
        var s = doc.createElement('style'); s.id = STY;
        s.textContent =
          '#' + BTN + '{position:fixed;z-index:2147483000;' +
          'bottom:calc(var(--nav-movil-alto) + 12px);left:12px;' +
          'width:40px;height:40px;padding:0;border:none;border-radius:50%;' +
          'cursor:pointer;background:#6c5ce7;color:#fff;font-size:18px;' +
          'line-height:40px;text-align:center;display:none;' +
          'box-shadow:0 3px 10px rgba(76,60,180,.35);}' +
          '#' + BTN + ':active{transform:scale(.94);}' +
          '@media (max-width:900px){#' + BTN + '{display:block;}}';
        doc.head.appendChild(s);
      }
      function ensureBtn(){
        if (doc.getElementById(BTN)) return;
        var b = doc.createElement('button');
        b.id = BTN; b.type = 'button';
        b.title = 'Pantalla completa';
        b.setAttribute('aria-label', 'Pantalla completa');
        b.innerHTML = '\\u26F6';
        b.onclick = toggle;
        doc.body.appendChild(b);
        doc.addEventListener('fullscreenchange', function(){
          b.innerHTML = fsOn() ? '\\u2715' : '\\u26F6';
        });
      }
      function check(){
        if (doc.body && doc.head){ ensureStyle(); ensureBtn(); }
        else if (tries++ < MAX) setTimeout(check, 250);
      }
      check();
    })();
    </script>
    """, height=0)
def inject_sello_actualizacion(rotulo, valor, color=None):
    """Pinta `<rotulo> <valor>` como div fijo en el body del documento de la
    app: los contenedores de Streamlit crean stacking contexts que dejaban el
    texto ENTERRADO bajo el cromo fijo por más z-index que tuviera; anclado
    directo al body escapa de todos ellos.

    2026-09-08 — DE PIE A SELLO DE LA CABECERA
        Se llamaba `inject_footer_actualizacion` y vivía abajo a la
        izquierda, dentro de la franja blanca fija que cerraba el área de
        contenido. Esa franja se eliminó a pedido ("eliminemos la franja
        inferior, ese texto pongámoslo en la franja superior de reportes,
        pero alineado a la derecha") y el texto se mudó al extremo derecho
        de la franja de REPORTES.

        Sigue siendo un div `fixed` colgado del body y NO un `st.markdown`
        dentro de `st.container(key="nav_franja_rep")`, por dos motivos:
          · la franja centra sus botones con `justify-content: safe center`
            (`estilos/_20_compras_rail.py`, a pedido del 2026-08-31), y
            meterle un hijo más los descentraría — el texto no es un ítem
            de esa navegación, se apoya en su caja;
          · `inject_navegacion()` (que dibuja la franja) corre en app.py:141
            y la antigüedad del dato no se conoce hasta app.py:617, después
            de resolver `cfg`. Ponerlo dentro obligaría a reordenar eso.

        Se alinea con los BOTONES, no con la caja: la franja mide 36px (48
        hasta el 2026-09-12) pero sus botones van pegados al tope
        (`align-items: flex-start` + 1px de padding, 30px de alto), así que
        centrarlo en la franja lo dejaría más abajo que los nombres de los
        reportes. De ahí `top:1px` +
        `height:30px` — los mismos tres números que los botones.

    POR QUÉ EL RÓTULO Y EL VALOR VAN SEPARADOS
        Porque el sello y la navegación se disputan el mismo renglón y hay
        anchos donde no entran los dos. Medido en el navegador a 1440
        (12px, DM Sans): el grupo de los 6 botones mide 608px y va CENTRADO,
        así que su borde derecho está en `W/2 + 304`; el sello arranca en
        `W - 16 - ancho`. Los cuatro anchos que puede tener el sello:

            «Última actualización: 07/09/2026 · 03:00»            230px
            … + « · hace 12 días» (dato viejo)                    290px
            sólo el valor «07/09/2026 · 03:00»                    109px
            … + « · hace 12 días»                                 186px

        Con 24px de aire mínimo, el ancho al que se tocan es
        `2 * (304 + 16 + ancho + 24)`: 1268px con el rótulo puesto y el dato
        viejo, 1060px sin rótulo. De ahí los dos cortes del `<style>` de
        abajo — 1280 y 1060. Se elige encoger antes que desaparecer: por
        debajo de 1280 el rótulo sobra (el valor es una fecha, se lee sola)
        y sólo por debajo de 1060 se va el sello entero.

        NO se resuelve con `padding` en la franja: darle sitio al sello con
        un padding derecho descentraría los botones, y hacerlo simétrico
        (para que sigan centrados) obligaría a la franja a scrollear por
        debajo de 1100px — dejar un nombre de reporte fuera de pantalla es
        peor que dejar fuera la hora del dato.

    `color`: color CSS del texto; None deja el gris de siempre. Lo usa
    app.py para que el sello se ponga ámbar cuando el dato está viejo (ver
    data.HORAS_DATO_VIEJO) — el aviso de arriba se lee y se ignora, este
    queda."""
    _r = json.dumps(str(rotulo))
    _v = json.dumps(str(valor))
    _c = json.dumps(str(color) if color else "#71717a")
    inyectar_html("""
    <script>
    (function(){
        var doc = window.parent.document;
        var el = doc.getElementById('sello-actualizacion');
        if (!el) {
            el = doc.createElement('div');
            el.id = 'sello-actualizacion';
            /* Los 16px de `right` son el padding lateral de la franja
               (`padding: 1px 16px 0 16px` en _20_compras_rail.py): así el
               texto termina en la misma línea vertical en la que termina
               su contenido, no contra el vidrio. */
            el.style.cssText = 'position:fixed;right:16px;top:1px;'
                + 'height:30px;display:flex;align-items:center;gap:4px;'
                + 'z-index:2147483647;font-size:12px;color:#71717a;'
                + "font-family:'DM Sans',sans-serif;pointer-events:none;"
                + 'white-space:nowrap;';
            /* Dos hijos y no un textContent suelto: el rótulo se esconde
               solo cuando la franja se queda sin sitio (ver el docstring).
               `textContent` en los dos, nunca innerHTML — el valor lleva
               una fecha formateada en app.py, no HTML. */
            var rot = doc.createElement('span');
            rot.className = 'sello-rotulo';
            var val = doc.createElement('span');
            val.className = 'sello-valor';
            el.appendChild(rot);
            el.appendChild(val);
            doc.body.appendChild(el);
        }
        if (!doc.getElementById('sello-actualizacion-css')) {
            var stl = doc.createElement('style');
            stl.id = 'sello-actualizacion-css';
            /* En movil no hay franja de reportes donde apoyarse (la esconde
               `estilos/_99_movil.py`): el sello se queda abajo a la
               izquierda, por encima de los 60px de la barra de navegacion
               inferior. Se resetean top/right/height porque el estilo
               inline de arriba los deja puestos, pero NO el `display:flex`
               — el espacio entre el rotulo y el valor es el `gap`, y con
               `display:block` los dos <span> quedaban pegados
               ("Ultima actualizacion:07/09/2026"), medido en el navegador.
               El rotulo no hace falta devolverlo: los dos cortes de arriba
               llevan `min-width:769px`, asi que aca nunca se esconde (abajo
               no compite con nadie por el renglon). */
            stl.textContent = '@media (max-width:1280px) and (min-width:769px) {'
                + ' #sello-actualizacion .sello-rotulo { display: none; } }'
                + '@media (max-width:1060px) and (min-width:769px) {'
                + ' #sello-actualizacion { display: none !important; } }'
                + '@media (max-width:768px) {'
                + ' #sello-actualizacion {'
                + '   left: 12px !important; bottom: 68px !important;'
                + '   top: auto !important; right: auto !important;'
                + '   height: auto !important;'
                /* PASTILLA, solo en movil. En escritorio el sello se apoya
                   en la franja de reportes, que es opaca y por la que el
                   contenido pasa POR DEBAJO; aca no hay franja, asi que sin
                   un fondo propio el texto queda flotando sobre lo que se
                   este scrolleando (medido: se leia encima del grafico de
                   Evolucion). La franja blanca que hacia ese trabajo hasta
                   el 2026-09-08 se elimino con todo lo demas. */
                + '   background: var(--bg-card, #fff) !important;'
                + '   padding: 3px 8px !important;'
                + '   border: 1px solid var(--border, #e4e4e7) !important;'
                + '   border-radius: 6px !important;'
                + ' } }';
            doc.head.appendChild(stl);
        }
        /* El color y los textos se aplican FUERA del if(!el): el elemento se
           crea una sola vez y en los reruns siguientes sólo se actualiza su
           contenido, así que si esto viviera adentro, el sello se quedaría
           con el color y la hora del primer render y no podría volver a gris
           al normalizarse. */
        el.style.color = """ + _c + """;
        el.querySelector('.sello-rotulo').textContent = """ + _r + """;
        el.querySelector('.sello-valor').textContent = """ + _v + """;
    })();
    </script>
    """, height=0)
def inject_calendario_es():
    """Traduce a español el calendario nativo de Streamlit (BaseWeb): meses,
    abreviaturas de días, el desplegable de meses y el texto de ayuda.

    Streamlit/BaseWeb no exponen un parámetro de idioma, así que se traduce
    por TEXTO (las clases son dinámicas y cambian entre versiones). Un
    MutationObserver reaplica la traducción cuando el calendario o el
    desplegable de meses aparecen: el desplegable se renderiza FUERA del
    popover del calendario (como [role=listbox]), por eso se observa el
    documento entero y se recorren popovers/listboxes (barato: si no hay
    ninguno abierto, no hace nada).

    Verificado en la app publicada: meses, días (Lu Ma Mi Ju Vi Sá Do),
    desplegable de meses y "Elige un rango de fechas".
    """
    inyectar_html(r"""
    <script>
    (function(){
        var doc = window.parent.document;
        var win = window.parent;
        if (doc.__calEsInit) return;
        doc.__calEsInit = true;

        var MESES = {January:'Enero',February:'Febrero',March:'Marzo',
            April:'Abril',May:'Mayo',June:'Junio',July:'Julio',
            August:'Agosto',September:'Septiembre',October:'Octubre',
            November:'Noviembre',December:'Diciembre'};
        var DIAS = {Mo:'Lu',Tu:'Ma',We:'Mi',Th:'Ju',Fr:'Vi',Sa:'Sá',Su:'Do'};
        var DIAS_L = {Monday:'lunes',Tuesday:'martes',Wednesday:'miércoles',
            Thursday:'jueves',Friday:'viernes',Saturday:'sábado',Sunday:'domingo'};

        function traducir(){
            // Solo zonas relevantes (popover del calendario, desplegables).
            // Si no hay ninguna abierta, querySelectorAll no devuelve nada.
            var zonas = doc.querySelectorAll(
                '[data-baseweb="popover"], [role="listbox"]');
            for (var z = 0; z < zonas.length; z++){
                var zona = zonas[z];
                var w = doc.createTreeWalker(zona, NodeFilter.SHOW_TEXT, null);
                var n;
                while ((n = w.nextNode())){
                    var t = n.textContent.trim();
                    if (MESES[t]) n.textContent = MESES[t];
                    else if (DIAS[t]) n.textContent = DIAS[t];
                    else if (/^Choose a date range$/i.test(t))
                        n.textContent = 'Elige un rango de fechas';
                }
                // aria-labels de los días (lector de pantalla / tooltip).
                try {
                    var etiq = zona.querySelectorAll('[aria-label]');
                    for (var e = 0; e < etiq.length; e++){
                        var el = etiq[e], a = el.getAttribute('aria-label'), o = a;
                        for (var k in MESES)
                            a = a.replace(new RegExp('\\b'+k+'\\b','g'), MESES[k]);
                        for (var k2 in DIAS_L)
                            a = a.replace(new RegExp('\\b'+k2+'\\b','g'), DIAS_L[k2]);
                        a = a.replace(/^Choose /, 'Elegir ');
                        if (a !== o) el.setAttribute('aria-label', a);
                    }
                } catch(err) {}
            }
        }

        var obs = new MutationObserver(function(){
            win.clearTimeout(doc.__calEsT);
            doc.__calEsT = win.setTimeout(traducir, 30);
        });
        obs.observe(doc.body, {childList: true, subtree: true});
        traducir();
    })();
    </script>
    """, height=0)
