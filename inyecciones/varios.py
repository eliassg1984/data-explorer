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
def inject_footer_actualizacion(texto):
    """Pinta el texto como div fijo en el body del documento de la app:
    los contenedores de Streamlit crean stacking contexts que dejaban el
    texto ENTERRADO bajo la franja inferior (.stApp::after) por más
    z-index que tuviera; anclado directo al body escapa de todos ellos."""
    _t = json.dumps(str(texto))
    inyectar_html("""
    <script>
    (function(){
        var doc = window.parent.document;
        var el = doc.getElementById('footer-actualizacion');
        if (!el) {
            el = doc.createElement('div');
            el.id = 'footer-actualizacion';
            /* 114px hasta el 2026-08-18: eran los 90 del rail izquierdo +
               24 de aire. Retirado el rail (hoy es la franja superior), el
               texto se alinea con el borde de la ventana. */
            el.style.cssText = 'position:fixed;left:24px;bottom:13px;'
                + 'z-index:2147483647;font-size:12px;color:#71717a;'
                + "font-family:'DM Sans',sans-serif;pointer-events:none;";
            doc.body.appendChild(el);
        }
        /* En movil la barra de navegacion inferior ocupa 60px: el texto
           sube para no solaparse con los iconos. */
        if (!doc.getElementById('footer-actualizacion-css')) {
            var stl = doc.createElement('style');
            stl.id = 'footer-actualizacion-css';
            stl.textContent = '@media (max-width:768px) {'
                + ' #footer-actualizacion {'
                + '   left: 12px !important; bottom: 68px !important;'
                + ' } }';
            doc.head.appendChild(stl);
        }
        el.textContent = """ + _t + """;
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
