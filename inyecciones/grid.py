"""inyecciones.grid - inyecciones que operan sobre el AgGrid.

Salud del grid, altura dinamica, maximizado con la Fullscreen API y el fix
del panel de columnas en Ajuste.

La altura se fija en px, no en 100%: encadenar porcentajes provoca reflow en
el hover de AgGrid y la tabla parpadea o colapsa (arquitectura.md #4).
"""

import json
import streamlit.components.v1 as components
from inyecciones._fragmentos import _FS_CSS_IFRAME, _JS_BUSCAR_IFRAME_FN, _PAG_CSS_BASE, _PAG_CSS_NATIVA


def inject_grid_health_check(usa_pagination_v2=False):
    """Comprueba que el grid de AgGrid se haya montado de verdad e inyecta
    CSS de paginación directamente dentro del iframe para garantizar que los
    estilos pisen los del tema nativo (balham/material).

    Los errores de render DENTRO del iframe de AgGrid (p.ej. un cellRenderer/
    JsCode que devuelve un nodo DOM → React #31) no llegan a la ventana
    principal, así que aquí inspeccionamos el iframe: si existe pero no aparece
    '.ag-root-wrapper' tras unos segundos, lo reportamos al overlay de errores.
    (No revisa el nº de filas: un grid vacío legítimo SÍ monta el wrapper.)

    Parámetro `usa_pagination_v2`:
        Cuando es True, el CSS se compone SOLO con _PAG_CSS_BASE (status bar,
        tool panel, contenedor .ag-paging-panel y page-size). Los estilos de
        botones/description/summary de la paginación nativa NO se inyectan
        porque `inject_pagination_v2` esconde esos elementos con
        position:absolute;left:-9999px y monta su propia barra #pgv2 encima
        del contenedor. Inyectarlos sería trabajo perdido sobre elementos
        invisibles.
        Cuando es False (default), se añade también _PAG_CSS_NATIVA. Es el
        caso de Salidas, Requerimientos y la vista móvil, donde la
        paginación nativa sí se ve.

    NOTA — colores del PAG_CSS:
        Este CSS se inyecta con fdoc.head.appendChild dentro del iframe de
        AgGrid, así que los var(--x) del :root del padre no resolverían.
        Se usan bloques pre-computados con los colores de tema.py ya
        resueltos con f-string. Ver arquitectura.md §Fase 2.
    """
    css = _PAG_CSS_BASE if usa_pagination_v2 else (_PAG_CSS_BASE + _PAG_CSS_NATIVA)
    pag_css_js = json.dumps(css)
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var tries = 0, MAX = 50;

      var PAG_CSS = """ + pag_css_js + """;

      function inyectarCSS(fdoc) {
        if (fdoc.getElementById('pag-custom-css')) return;
        var s = fdoc.createElement('style');
        s.id = 'pag-custom-css';
        s.textContent = PAG_CSS;
        fdoc.head.appendChild(s);
      }

      function check(){
        tries++;
        var frames = doc.querySelectorAll('iframe[src*="st_aggrid"]');
        if (frames.length === 0){
          if (tries < MAX) setTimeout(check, 500);
          return;
        }
        var montado = false;
        for (var i = 0; i < frames.length; i++){
          var d = null;
          try { d = frames[i].contentDocument; } catch(e){}
          if (!d) continue;
          if (d.querySelector('.ag-root-wrapper')) {
            montado = true;
            inyectarCSS(d);
          }
        }
        if (montado){
          // Auto-correccion: si el aviso ya se mostro (grid lento) y el grid
          // termino montando bien, retirarlo del panel.
          if (win.__gridErrReported && win.__errLog){
            win.__errLog = win.__errLog.filter(function(m){
              return String(m).indexOf('Tabla no renderizada') === -1;
            });
            win.__gridErrReported = false;
            if (win.__errRender) win.__errRender();
          }
          return;
        }
        if (tries < MAX){ setTimeout(check, 500); return; }
        if (win.__logErr && !win.__gridErrReported){
          win.__gridErrReported = true;
          win.__logErr('Tabla no renderizada: el grid de AgGrid no se monto '
            + 'tras 25s (carga lenta o cellRenderer/JsCode invalido - React #31).');
          tries = 0;  // seguir vigilando: si monta tarde, se auto-retira el aviso
          setTimeout(check, 500);
        }
      }
      setTimeout(check, 800);
    })();
    </script>
    """, height=0)
def inject_maximize_aggrid():
    """
    Botón ⛶ para poner la tabla AgGrid en PANTALLA COMPLETA NATIVA (Fullscreen
    API). El fullscreen se pide desde el documento padre sobre el ELEMENTO
    iframe (iframe.requestFullscreen()), así que NO hace falta allow="fullscreen".

    UBICACIÓN DEL BOTÓN (cambio nuevo):
    - Con sidebar: el ⛶ se ancla como PRIMER ítem del riel (.ag-side-buttons),
      DENTRO del iframe. Sitio fijo, se desplaza con la tabla. (Antes flotaba
      con position:fixed y se "despegaba" al hacer scroll.)
    - Sin sidebar (p.ej. Salidas con sideBar=False): se conserva el botón
      flotante como respaldo, pero reubicándolo también al hacer scroll.

    El clic ocurre dentro del iframe, pero la activación de usuario se propaga
    al padre, así que iframe.requestFullscreen() sigue siendo válido (misma
    técnica que el botón ✕ de salida ya existente).

    Esc sale de forma nativa; 'fullscreenchange' restaura la altura del grid.
    Safari usa la variante webkit* (fallback incluido).

    NOTA — colores:
      - `aggrid-fs-css` va DENTRO del iframe (fdoc.head.appendChild). Antes
        usaba var(--x) que no resolvía → el ⛶ del riel salía transparente y
        el ✕ de salida con estilos por defecto. Ahora usa el bloque pre-
        computado _FS_CSS_IFRAME con constantes de tema.py.
      - `aggrid-max-css-flot` va AL PADRE (doc.head). Ese SÍ ve el :root de
        estilos.py, así que sigue usando var(--x) sin cambios.
    """
    fs_css_js = json.dumps(_FS_CSS_IFRAME)
    components.html("""
    <script>
    (function(){
        var win = window.parent;
        var doc = win.document;
        var BTN_ID  = 'aggrid-maximize-btn';
        var EXIT_ID = 'aggrid-exit-fs-btn';
        var tries = 0;
        var MAX = 40;
        var iframeFS = null;
        var btnFlotante = null;   // SOLO se crea si la tabla no tiene riel

        var FS_CSS = """ + fs_css_js + """;
        """ + _JS_BUSCAR_IFRAME_FN + """

        function elementoFS() {
            return doc.fullscreenElement || doc.webkitFullscreenElement || null;
        }

        function salirFS() {
            if (doc.exitFullscreen)            doc.exitFullscreen();
            else if (doc.webkitExitFullscreen) doc.webkitExitFullscreen();
        }

        function toggle() {
            if (elementoFS()) { salirFS(); return; }
            var iframe = buscarIframe();
            if (!iframe) return;
            iframeFS = iframe;
            prepararIframe(iframe);
            if (iframe.requestFullscreen)            iframe.requestFullscreen();
            else if (iframe.webkitRequestFullscreen) iframe.webkitRequestFullscreen();
        }

        /* CSS + botón ✕ DENTRO del iframe (lo único visible en fullscreen),
           MÁS el estilo del ⛶ del riel. */
        function prepararIframe(iframe) {
            var fdoc = null;
            try { fdoc = iframe.contentDocument; } catch(e) {}
            if (!fdoc || !fdoc.body) return;

            if (!fdoc.getElementById('aggrid-fs-css')) {
                var s = fdoc.createElement('style');
                s.id = 'aggrid-fs-css';
                s.textContent = FS_CSS;
                fdoc.head.appendChild(s);
            }

            if (!fdoc.getElementById(EXIT_ID)) {
                var b = fdoc.createElement('button');
                b.id = EXIT_ID;
                b.innerHTML = '&#x2715;';
                b.title = 'Restaurar tabla (Esc)';
                b.onclick = salirFS;
                fdoc.body.appendChild(b);
            }
        }

        /* Ancla el ⛶ como PRIMER ítem del riel. Devuelve true si lo logró (o si
           ya estaba puesto). Devuelve false si la tabla no tiene riel. */
        function anclarEnRiel(iframe) {
            var fdoc = null;
            try { fdoc = iframe.contentDocument; } catch(e) {}
            if (!fdoc) return false;
            var riel = fdoc.querySelector('.ag-side-buttons');
            if (!riel) return false;
            if (fdoc.getElementById(BTN_ID)) return true;
            var b = fdoc.createElement('button');
            b.id = BTN_ID;
            b.type = 'button';
            b.innerHTML = '&#x26F6;';
            b.title = 'Maximizar tabla';
            b.onclick = toggle;
            riel.insertBefore(b, riel.firstChild);
            return true;
        }

        /* Fallback (SOLO tablas sin riel): botón flotante, reubicado también al
           hacer scroll para que no se despegue. */
        function posicionarFlotante(iframe) {
            if (!btnFlotante || !iframe || elementoFS()) return;
            var r = iframe.getBoundingClientRect();
            btnFlotante.style.top   = (r.top + 8) + 'px';
            btnFlotante.style.right = (win.innerWidth - r.right + 8) + 'px';
        }

        function crearFlotante(iframe) {
            /* Este CSS va al doc.head del PADRE, así que sí ve el :root de
               estilos.py y puede seguir usando var(--x). */
            if (!doc.getElementById('aggrid-max-css-flot')) {
                var s = doc.createElement('style');
                s.id = 'aggrid-max-css-flot';
                s.textContent = [
                    '#' + BTN_ID + '-flot {',
                    '  position: fixed;',
                    '  z-index: 99999;',
                    '  width: 30px;',
                    '  height: 30px;',
                    '  border: 1px solid var(--border);',
                    '  border-radius: 6px;',
                    '  background: var(--bg-secondary);',
                    '  color: var(--text-secondary);',
                    '  font-size: 15px;',
                    '  cursor: pointer;',
                    '  display: flex;',
                    '  align-items: center;',
                    '  justify-content: center;',
                    '  box-shadow: 0 1px 4px rgba(0,0,0,0.10);',
                    '  transition: background .15s, color .15s, border-color .15s;',
                    '  line-height: 1;',
                    '}',
                    '#' + BTN_ID + '-flot:hover {',
                    '  background: var(--accent-tint);',
                    '  border-color: var(--focus-lavender);',
                    '  color: var(--accent-hover);',
                    '}',
                ].join('\\n');
                doc.head.appendChild(s);
            }
            if (!btnFlotante) {
                btnFlotante = doc.createElement('button');
                btnFlotante.id = BTN_ID + '-flot';
                btnFlotante.innerHTML = '&#x26F6;';
                btnFlotante.title = 'Maximizar tabla';
                btnFlotante.onclick = toggle;
                doc.body.appendChild(btnFlotante);
                /* Reposiciona al hacer scroll (solo mueve el botón; NO fuerza
                   resize del iframe, así que no dispara el bucle React #185). */
                win.addEventListener('scroll', function() {
                    posicionarFlotante(buscarIframe());
                }, true);
            }
            posicionarFlotante(iframe);
        }

        function onFSChange() {
            var activo = (elementoFS() === iframeFS) && iframeFS !== null;
            var fdoc = null, fwin = null;
            if (iframeFS) {
                try { fdoc = iframeFS.contentDocument; } catch(e) {}
                fwin = iframeFS.contentWindow;
            }
            if (fdoc && fdoc.documentElement) {
                fdoc.documentElement.classList.toggle('fs-activo', activo);
            }
            if (activo && fwin) {
                win.setTimeout(function() {
                    try { fwin.dispatchEvent(new Event('resize')); } catch(e) {}
                }, 250);
            }
            /* El ⛶ del riel se oculta/muestra por CSS (.fs-activo). Solo hay que
               gestionar el flotante si existe. */
            if (btnFlotante) {
                btnFlotante.style.display = activo ? 'none' : 'flex';
                if (!activo) {
                    win.setTimeout(function() {
                        posicionarFlotante(iframeFS || buscarIframe());
                    }, 100);
                }
            }
        }
        doc.addEventListener('fullscreenchange', onFSChange);
        doc.addEventListener('webkitfullscreenchange', onFSChange);

        /* Congela la negociación de altura Streamlit<->componente durante el
           fullscreen (evita el bucle setFrameHeight->resize->re-medición que
           acaba en React #185). Igual que antes. */
        win.addEventListener('message', function(ev){
            if (!iframeFS || elementoFS() !== iframeFS) return;
            var d = ev.data;
            if (d && d.type === 'streamlit:setFrameHeight'
                  && ev.source === iframeFS.contentWindow){
                ev.stopImmediatePropagation();
            }
        }, true);

        function check() {
            tries++;
            var iframe = buscarIframe();
            if (iframe) {
                prepararIframe(iframe);              // estilos + ✕ + estilo del ⛶
                if (anclarEnRiel(iframe)) return;    // con sidebar → ⛶ en el riel
                if (tries >= 6) {                    // sin sidebar → flotante
                    crearFlotante(iframe);
                    return;
                }
            }
            if (tries < MAX) win.setTimeout(check, 500);
        }
        win.setTimeout(check, 800);
    })();
    </script>
    """, height=0)
def inject_dynamic_grid_height(offset_px: int = 260, min_px: int = 320):
    """
    Estira la tabla AgGrid para que ocupe el alto de pantalla disponible,
    en lugar del height=... fijo con el que se renderiza.

    DISEÑO SEGURO (mismo espíritu que inject_maximize_aggrid):
    - El grid se sigue creando con su height fijo en tablas/desktop.py. Esta función
      solo lo AGRANDA por CSS/JS después. Si algo falla, el fijo queda como
      red de seguridad: comenta la llamada y vuelves al estado anterior.
    - Mide window.innerHeight UNA sola vez (con reintentos hasta que el iframe
      exista). NO instala listener de resize continuo, que es justo lo que
      provoca el bucle de re-medición (setFrameHeight -> resize -> re-mide...)
      y el error React #185. Es una medición puntual, no reactiva.
    - Reutiliza el mismo buscarIframe() que el fullscreen: localiza el iframe
      del componente por su .ag-root-wrapper.

    Parámetros:
    - offset_px: píxeles reservados para lo que hay ARRIBA de la tabla
      (chip de título, tabs, fecha) más un margen inferior. Súbelo si la
      tabla tapa algo de abajo; bájalo si queda blanco.
    - min_px: altura mínima; en pantallas muy bajas no baja de aquí.

    NOTA — colores: el `dynh-css` que inyecta esta función dentro del iframe
    solo trae `html, body {margin:0}` y `.ag-root-wrapper {height: Npx}`.
    No usa colores, así que no aplica la migración del punto 4.
    """
    # Config como línea JS separada (f-string sin % ni {} conflictivos),
    # y el resto del script como literal puro: así ningún % del CSS/JS
    # (p.ej. height:100%) choca con el formateo de Python.
    config_js = f"var OFFSET = {int(offset_px)}; var MINPX = {int(min_px)};"

    components.html("""
    <script>
    (function(){
        var win = window.parent;
        var doc = win.document;
        """ + config_js + """
        var tries = 0;
        var MAX = 40;
        """ + _JS_BUSCAR_IFRAME_FN + """

        function aplicarAltura() {
            var iframe = buscarIframe();
            if (!iframe) return false;

            /* Alto disponible = ventana - lo que va arriba/abajo (offset). */
            var h = Math.max(MINPX, win.innerHeight - OFFSET);

            /* 1) El iframe del componente. */
            iframe.style.height = h + 'px';

            /* 2) El contenedor que Streamlit envuelve alrededor del iframe,
                  para que no lo recorte a su altura reportada. */
            var cont = iframe.parentElement;
            for (var k = 0; k < 3 && cont; k++) {
                cont.style.height = h + 'px';
                cont = cont.parentElement;
            }

            /* 3) Cadena COMPLETA de alturas dentro del iframe.
               No basta con el wrapper: el body trae margen por defecto
               (~8px arriba/abajo) y la barra de paginación personalizada
               (inject_pagination_v2) es más alta que la nativa; sin fijar
               toda la cadena, el contenido excede al iframe y la paginación
               se ve CORTADA abajo. Con html/body/tema/wrapper al 100% y
               margin 0, contenido == iframe, siempre, mida lo que mida
               la barra. */
            try {
                var idoc = iframe.contentDocument;
                var hInner = h;  /* misma altura en PX que el iframe */
                if (idoc && idoc.head) {
                    var prev = idoc.getElementById('dynh-css');
                    /* CSS con altura FIJA en px (no 100% encadenado).
                       Motivo: html/body/tema/wrapper todos a 100% forman una
                       cadena relativa que se recalcula entre sí; al hacer hover
                       AgGrid dispara reflow, el 100% se re-mide en bucle y la
                       tabla PARPADEA o colapsa a 0 (queda en blanco). Fijar el
                       wrapper a un px concreto rompe la cadena: no hay nada que
                       recalcular. Se actualiza el px en cada aplicarAltura. */
                    var css =
                        'html, body { margin: 0; }' +
                        '.ag-root-wrapper { height: ' + hInner + 'px !important; }';
                    if (prev) {
                        prev.textContent = css;
                    } else {
                        var stl = idoc.createElement('style');
                        stl.id = 'dynh-css';
                        stl.textContent = css;
                        idoc.head.appendChild(stl);
                    }
                }
                /* Un ÚNICO resize diferido para que AgGrid recalcule las filas
                   visibles con la nueva altura. Puntual, no en bucle. */
                if (iframe.contentWindow) {
                    win.setTimeout(function(){
                        try { iframe.contentWindow.dispatchEvent(new Event('resize')); } catch(e) {}
                    }, 200);
                }
            } catch(e) {}

            return true;
        }

        function check() {
            tries++;
            if (aplicarAltura()) return;
            if (tries < MAX) win.setTimeout(check, 500);
        }
        win.setTimeout(check, 800);
    })();
    </script>
    """, height=0)
def inject_fix_column_panel_ajuste():
    """
    Fix para el panel Columnas de Ajuste de Inventario:
    AgGrid calcula top:N*32px al montar (tema material, 32px por defecto).
    Las pastillas miden ~52px, así que se enciman.
    Este JS entra al iframe y recalcula el top de cada ítem según su
    altura real medida en el DOM, sin tocar la virtualización.
    Se re-ejecuta cada vez que el panel abre (MutationObserver).

    NOTA — colores: esta función NO inyecta CSS, solo reposiciona con JS.
    No aplica la migración del punto 4.
    """
    components.html("""
    <script>
    (function(){
        var win = window.parent, doc = win.document;
        var tries = 0, MAX = 60;

        function reposicionar(fdoc) {
            // Aplica a ambos paneles: columns y pivotePanel
            var paneles = ['columns', 'pivotePanel'];
            paneles.forEach(function(panelId) {
                var sidebar = fdoc.querySelector(
                    ".ag-side-bar[data-active-panel='" + panelId + "']"
                );
                if (!sidebar) return;

                var items = sidebar.querySelectorAll(
                    '.ag-virtual-list-item'
                );
                if (!items.length) return;

                // Soltar el alto que dejó la corrida ANTERIOR antes de volver a medir.
                items.forEach(function(item) {
                    item.style.removeProperty('height');
                });
                void sidebar.offsetHeight;   // forzar reflow antes de medir

                var topAcum = 0;
                items.forEach(function(item) {
                    // Leer altura REAL del contenido (la pastilla con su padding/margin)
                    var inner = item.firstElementChild;
                    var alturaReal = inner
                        ? inner.getBoundingClientRect().height
                        : item.getBoundingClientRect().height;

                    // Margen mínimo entre pastillas
                    var alturaSlot = alturaReal + 4;

                    item.style.setProperty('top', topAcum + 'px', 'important');
                    item.style.setProperty('height', alturaSlot + 'px', 'important');
                    topAcum += alturaSlot;
                });

                // Ajustar altura total del container para que el scroll funcione
                var container = sidebar.querySelector('.ag-virtual-list-container');
                if (container) {
                    container.style.setProperty(
                        'height', topAcum + 'px', 'important'
                    );
                }
            });
        }

        function instalarObserver(fdoc) {
            // Observa cambios en el sidebar para re-ejecutar cuando
            // el usuario cambia de panel (Columnas ↔ Filtros ↔ Modo pivote)
            var sidebar = fdoc.querySelector('.ag-side-bar');
            if (!sidebar || sidebar.__fixObserver) return;

            var obs = new MutationObserver(function() {
                // Pequeño delay para que AgGrid termine de pintar los items
                win.setTimeout(function() { reposicionar(fdoc); }, 80);
            });
            obs.observe(sidebar, {
                attributes: true,
                attributeFilter: ['data-active-panel'],
                subtree: true,
                childList: true
            });
            sidebar.__fixObserver = obs;

            // Ejecutar una vez al instalar
            reposicionar(fdoc);
        }

        """ + _JS_BUSCAR_IFRAME_FN + """

        function check() {
            tries++;
            var iframe = buscarIframe();
            // La constante estándar devuelve el ELEMENTO iframe (no el
            // contentDocument). Aquí necesitamos el documento para instalar
            // el observer sobre .ag-side-bar, así que accedemos a .contentDocument.
            // buscarIframe() ya validó que .ag-root-wrapper existe, así que
            // el documento es seguro de usar.
            var fdoc = iframe ? iframe.contentDocument : null;
            if (fdoc) {
                instalarObserver(fdoc);
                return;
            }
            if (tries < MAX) win.setTimeout(check, 500);
        }
        win.setTimeout(check, 900);
    })();
    </script>
    """, height=0)
