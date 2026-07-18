"""
Inyecciones de HTML/JS en la página: overlay de errores, health-check
del grid de AgGrid, botón flotante del sidebar e inspector de elementos.

REGLA CLAVE (ver arquitectura.md §Fase 2):
  El :root del documento padre NO cruza la frontera del iframe de AgGrid.
  El CSS que se inyecta DENTRO del iframe debe usar colores literales
  (constantes de tema.py resueltas en Python via f-string). Solo el CSS
  que se añade al documento PADRE puede usar `var(--x)` de estilos.py.

Todos los bloques inyectados en `fdoc.head`/`agDoc.head`/`idoc.head` de un
iframe siguen esa regla. Los que se añaden a `doc.head` (padre) siguen
usando `var(--x)`. Las excepciones documentadas (colores literales del
overlay de errores y del inspector) se mantienen.
"""

import json
import streamlit as st
import streamlit.components.v1 as components

from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO,
    BLANCO, EXIT_HOVER,
    GRIS_BORDE, GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_SUAVE,
    ICON_MUTED, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO,
    LAVANDA_FOCO, SCROLL_THUMB, TEXTO_PRINCIPAL,
)


# ===========================================================================
# Fragmentos JS compartidos entre inyecciones (extraídos para no duplicar).
# ---------------------------------------------------------------------------
# Cada `components.html()` corre en un realm de JavaScript aislado, así que no
# pueden compartir funciones en runtime; la deduplicación se hace en Python,
# insertando el mismo string en cada inyección. Si mañana cambia el selector
# del iframe de AgGrid, se toca aquí en un solo sitio.
# ===========================================================================

_JS_BUSCAR_IFRAME_FN = """
        function buscarIframe() {
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"]');
            if (!frames.length) frames = doc.querySelectorAll('iframe');
            for (var i = 0; i < frames.length; i++) {
                try {
                    var d = frames[i].contentDocument;
                    if (d && d.querySelector('.ag-root-wrapper')) return frames[i];
                } catch(e) {}
            }
            return null;
        }
"""

# ===========================================================================
# CSS pre-computado en Python (colores resueltos con f-string).
# ---------------------------------------------------------------------------
# Estos bloques se inyectan DENTRO del iframe de AgGrid. Antes usaban
# var(--x) pero como el iframe no ve el :root del padre, todas esas
# variables caían al valor inicial del navegador (botones de paginación
# sin fondo, ⛶ del riel sin color acento, ✕ de fullscreen con estilos por
# defecto). Ahora usan constantes literales de tema.py.
#
# Se calculan una sola vez al importar el módulo y se pasan al JS con
# json.dumps() → así no hay que escapar las llaves del JavaScript.
# ===========================================================================

# --- inject_grid_health_check: paginación nativa + status bar + tool panel ---
#
# El CSS de paginación va PARTIDO EN DOS para no inyectar reglas inertes:
#
#   _PAG_CSS_BASE: siempre útil. Trae:
#     - .ag-status-bar y sus valores (barra de estado abajo del grid).
#     - .ag-filter-toolpanel + scrollbar.
#     - .ag-paging-panel (contenedor): pagination_v2 mete #pgv2 DENTRO de
#       este contenedor, así que su fondo/borde/altura/padding también le
#       aprovechan al look custom.
#     - .ag-paging-page-size (label + select del "50 filas por página"):
#       pagination_v2 lo reposiciona a la izquierda pero sigue visible,
#       así que sus estilos también sirven a ambos casos.
#
#   _PAG_CSS_NATIVA: solo tiene sentido cuando NO va a correr
#   inject_pagination_v2. Trae los elementos que pagination_v2 esconde con
#   position:absolute;left:-9999px (botones ‹›«», description, summary).
#   Si los inyectáramos igual, aplicarían sobre elementos invisibles: puro
#   trabajo perdido. Se usan en Salidas/Requerimientos/móvil, donde la
#   paginación nativa sí se ve.
_PAG_CSS_BASE = f"""
.ag-status-bar {{
  background: {GRIS_FONDO} !important;
  border-top: 1px solid {GRIS_BORDE} !important;
  color: {GRIS_TEXTO} !important;
  padding: 4px 16px !important;
  font-size: 12px !important;
  background-image: none !important;
  background-color: {GRIS_FONDO} !important;
}}
.ag-status-bar * {{
  background-image: none !important;
}}
.ag-status-name-value {{ color: {GRIS_TEXTO} !important; font-size: 12px !important; }}
.ag-status-name-value-value {{ color: {TEXTO_PRINCIPAL} !important; font-weight: 600 !important; }}

/* Barra INTEGRADA al pie de la tabla: mismo marco que el grid (sin
   tarjeta aparte), solo un divisor arriba y las esquinas inferiores
   del propio card. */
.ag-paging-panel {{
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  background: {BLANCO} !important;
  background-image: none !important;
  border: none !important;
  border-top: 1px solid {GRIS_BORDE} !important;
  border-radius: 0 0 12px 12px !important;
  margin-top: 0 !important;
  padding: 8px 16px !important;
  min-height: 44px !important;
  font-size: 12px !important;
  color: {ICON_MUTED} !important;
}}

/* AUTO-OCULTAR con una sola página: si ‹ y › están ambos deshabilitados
   no hay nada que paginar. Cubre la paginación nativa y la v2 (que solo
   mueve los botones fuera de pantalla; sus estados disabled siguen
   actualizándose). AgGrid moderno marca los botones con data-ref; se
   mantiene la variante ref por compatibilidad con versiones previas. */
.ag-paging-panel:has([ref="btPrevious"].ag-disabled):has([ref="btNext"].ag-disabled),
.ag-paging-panel:has([data-ref="btPrevious"].ag-disabled):has([data-ref="btNext"].ag-disabled) {{
  display: none !important;
}}

.ag-paging-page-size {{ order: -1 !important; margin-right: auto !important; }}
.ag-paging-page-size .ag-label {{ color: {ICON_MUTED} !important; font-size: 12px !important; margin-right: 6px !important; }}
.ag-paging-page-size .ag-select, .ag-paging-page-size select {{
  border: 1px solid {GRIS_BORDE} !important;
  border-radius: 6px !important;
  background: {BLANCO} !important;
  color: {TEXTO_PRINCIPAL} !important;
  font-size: 12px !important;
  padding: 2px 6px !important;
}}

.ag-filter-toolpanel {{
  border: none !important;
  border-radius: 0 !important;
  margin: 0 !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}}
.ag-filter-toolpanel::-webkit-scrollbar {{ width: 8px; }}
.ag-filter-toolpanel::-webkit-scrollbar-track {{ background: transparent; }}
.ag-filter-toolpanel::-webkit-scrollbar-thumb {{ background: {SCROLL_THUMB}; border-radius: 4px; }}
"""

_PAG_CSS_NATIVA = f"""
.ag-paging-row-summary-panel {{ color: {ICON_MUTED} !important; font-size: 12px !important; }}
.ag-paging-row-summary-panel-number {{ color: {TEXTO_PRINCIPAL} !important; font-weight: 600 !important; }}

.ag-paging-description {{ color: {ICON_MUTED} !important; font-size: 12px !important; }}

.ag-paging-button {{
  width: 28px !important; height: 28px !important;
  border: 1px solid {GRIS_BORDE} !important;
  border-radius: 6px !important;
  background: {BLANCO} !important;
  color: {GRIS_TEXTO} !important;
  font-size: 14px !important;
  margin: 0 2px !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all 0.15s ease !important;
  position: relative !important;
}}
.ag-paging-button span, .ag-paging-button .ag-icon {{
  display: none !important;
}}
.ag-paging-button[ref="btFirst"]::after,
.ag-paging-button[data-ref="btFirst"]::after  {{ content: "«" !important; }}
.ag-paging-button[ref="btPrevious"]::after,
.ag-paging-button[data-ref="btPrevious"]::after {{ content: "‹" !important; }}
.ag-paging-button[ref="btNext"]::after,
.ag-paging-button[data-ref="btNext"]::after   {{ content: "›" !important; }}
.ag-paging-button[ref="btLast"]::after,
.ag-paging-button[data-ref="btLast"]::after   {{ content: "»" !important; }}
.ag-paging-button::after {{
  font-size: 16px !important;
  line-height: 1 !important;
  color: {GRIS_TEXTO} !important;
}}
.ag-paging-button:hover:not(.ag-disabled) {{
  background: {LAVANDA_FONDO} !important;
  border-color: {LAVANDA_FOCO} !important;
}}
.ag-paging-button:hover:not(.ag-disabled)::after {{
  color: {ACENTO_FUERTE} !important;
}}
.ag-paging-button.ag-disabled {{
  border-color: {GRIS_LINEA} !important;
  background: {GRIS_FONDO} !important;
  cursor: default !important;
  opacity: 0.4 !important;
}}
"""


# --- inject_pagination_v2: barra #pgv2 con números y salto (dentro del iframe) ---
_PGV2_CSS_IFRAME = f"""
.ag-paging-panel {{ position: relative !important; justify-content: center !important; }}
.ag-paging-panel .ag-paging-page-size {{
  position: absolute !important; left: 16px !important;
  top: 50% !important; transform: translateY(-50%) !important; margin: 0 !important;
}}
.ag-paging-panel .ag-paging-row-summary-panel,
.ag-paging-description,
.ag-paging-button {{
  position: absolute !important; left: -9999px !important; width: 1px !important;
  height: 1px !important; overflow: hidden !important;
}}
#pgv2 {{
  display: inline-flex; align-items: center; gap: 14px; margin: 0 auto;
  font: 13px -apple-system, BlinkMacSystemFont, sans-serif; color: {ICON_MUTED};
}}
#pgv2 .pgv2-pages {{ display: inline-flex; align-items: center; gap: 6px; }}
#pgv2 button {{
  min-width: 30px; height: 30px; padding: 0 8px;
  border: 1px solid {GRIS_BORDE};
  border-radius: 8px; background: {BLANCO}; color: {GRIS_TEXTO}; font-size: 13px;
  cursor: pointer; display: inline-flex; align-items: center;
  justify-content: center; transition: all .15s;
}}
#pgv2 button:hover:not(:disabled) {{
  background: {LAVANDA_FONDO};
  border-color: {LAVANDA_FOCO};
  color: {ACENTO_FUERTE};
}}
#pgv2 button:disabled {{ opacity: .4; cursor: default; }}
#pgv2 button.pgv2-on {{
  background: {ACENTO_FUERTE};
  border-color: {ACENTO_FUERTE};
  color: {BLANCO}; font-weight: 500;
}}
#pgv2 .pgv2-dots {{ color: {GRIS_TEXTO_SUAVE}; padding: 0 2px; }}
#pgv2 .pgv2-jump {{ display: inline-flex; align-items: center; gap: 7px; color: {GRIS_TEXTO}; }}
#pgv2 .pgv2-jump input {{
  width: 48px; height: 30px;
  border: 1px solid {GRIS_BORDE}; border-radius: 8px;
  text-align: center; color: {TEXTO_PRINCIPAL}; font-size: 13px;
  background: {BLANCO}; outline: none; -moz-appearance: textfield;
}}
#pgv2 .pgv2-jump input:focus {{
  border-color: {ACENTO_FUERTE};
  box-shadow: 0 0 0 2px {LAVANDA_CABECERA_GRUPO};
}}
#pgv2 .pgv2-jump input::-webkit-outer-spin-button,
#pgv2 .pgv2-jump input::-webkit-inner-spin-button {{
  -webkit-appearance: none; margin: 0;
}}
"""


# --- inject_maximize_aggrid: fullscreen + ⛶ integrado en el riel (dentro del iframe) ---
_FS_CSS_IFRAME = f"""
html.fs-activo, html.fs-activo body {{
  margin: 0 !important;
  height: 100vh !important;
  min-height: 100vh !important;
  max-height: 100vh !important;
  overflow: hidden !important;
}}
html.fs-activo #root {{
  height: 100vh !important;
  overflow: hidden !important;
}}
html.fs-activo #root > div {{
  height: 100vh !important;
}}
html.fs-activo #root [class*="ag-theme-"]:not(.ag-dnd-ghost):not(.ag-popup) {{
  height: 100vh !important;
}}
html.fs-activo .ag-dnd-ghost,
html.fs-activo .ag-popup,
html.fs-activo body > [class*="ag-theme-"]:not(#gridContainer) {{
  height: auto !important;
  min-height: 0 !important;
}}
html.fs-activo .ag-root-wrapper {{
  height: 100% !important; border-radius: 0 !important;
}}
html.fs-activo .ag-column-panel,
html.fs-activo .ag-filter-toolpanel {{
  height: 100% !important; overflow-y: auto !important;
}}
html.fs-activo .ag-column-drop-vertical {{
  flex: 0 0 auto !important;
  min-height: 3.2em !important;
}}
/* ── ⛶ integrado en el riel de pestañas ── */
#aggrid-maximize-btn {{
  width: 100%;
  height: 36px;
  border: none;
  border-bottom: 1px solid {ACENTO};
  background: {LAVANDA_FONDO};
  color: {ACENTO_FUERTE};
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: horizontal-tb;
  line-height: 1;
  transition: background .15s, color .15s;
}}
#aggrid-maximize-btn:hover {{
  background: {LAVANDA_FONDO};
  color: {ACENTO_FUERTE};
}}
/* En fullscreen ocultamos el ⛶ (ya hay ✕ de salida). */
html.fs-activo #aggrid-maximize-btn {{ display: none; }}
/* ── Botón de salida ✕ ── */
#aggrid-exit-fs-btn {{
  position: fixed;
  top: 12px;
  right: 44px;
  z-index: 99999;
  width: 30px;
  height: 30px;
  border: 1px solid {GRIS_TEXTO};
  border-radius: 6px;
  background: {TEXTO_PRINCIPAL};
  color: {GRIS_FONDO};
  font-size: 14px;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  line-height: 1;
}}
html.fs-activo #aggrid-exit-fs-btn {{ display: flex; }}
#aggrid-exit-fs-btn:hover {{ background: {EXIT_HOVER}; }}
"""


# ===========================================================================
# OVERLAY DE ERRORES EN PANTALLA (para diagnóstico sin F12)
# ===========================================================================

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
    components.html("""
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


# ===========================================================================
# INSPECTOR DE ELEMENTOS — tooltips de identificación para capturas de pantalla
# ===========================================================================

def inject_element_inspector():
    """
    Inspector de elementos v2 - tooltip enriquecido al pasar el cursor.
    Activacion : ?debug=1 en la URL  o  Alt+I

    Unificado con el resto de herramientas de desarrollo: el mismo ?debug=1
    que muestra el panel de diagnostico activa tambien este inspector.

    NOTA — colores: el tooltip (#el-inspector-tip) y el badge
    (#el-inspector-badge) se añaden a doc.body (documento PADRE), no al
    iframe de AgGrid, así que sus var(--x) SÍ resuelven contra el :root de
    estilos.py. Se mantienen tal cual.
    """
    components.html("""
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;

        function inspectorActivo() {
            return new URL(win.location.href).searchParams.get('debug') === '1';
        }

        var tip = doc.getElementById('el-inspector-tip');
        if (!tip) {
            tip = doc.createElement('div');
            tip.id = 'el-inspector-tip';
            tip.style.cssText = [
                'position:fixed',
                'pointer-events:none',
                'z-index:2147483647',
                // #101014: fondo casi negro del INSPECTOR (herramienta interna
                // de depuracion). Excepcion intencional.
                'background:#101014',
                'color:var(--border)',
                'font:12px/1.55 "Courier New",monospace',
                'padding:7px 11px',
                'border-radius:6px',
                'border:1px solid var(--accent)',
                'white-space:pre',
                'opacity:0',
                'transition:opacity 0.1s',
                'max-width:420px',
                'overflow:hidden',
                'box-shadow:0 3px 12px rgba(0,0,0,0.5)'
            ].join(';');
            doc.body.appendChild(tip);
        }

        var badge = doc.getElementById('el-inspector-badge');
        if (!badge) {
            badge = doc.createElement('div');
            badge.id = 'el-inspector-badge';
            badge.style.cssText = [
                'position:fixed','bottom:10px','left:72px','z-index:2147483646',
                'background:var(--accent-deep)','color:#fff',
                'font:600 11px/1 -apple-system,sans-serif',
                'padding:5px 10px','border-radius:20px','display:none',
                'align-items:center','gap:6px','box-shadow:0 2px 8px rgba(0,0,0,0.3)'
            ].join(';');
            badge.innerHTML = 'Inspector ON &nbsp;<span style="opacity:.6;font-weight:400">Alt+I para desactivar</span>';
            doc.body.appendChild(badge);
        }

        function actualizarBadge() {
            badge.style.display = inspectorActivo() ? 'flex' : 'none';
        }
        actualizarBadge();

        function txt(el) { return el ? el.textContent.trim() : ''; }

        function labelWidget(container) {
            var l = container.querySelector('label p');
            if (!l) l = container.querySelector('label');
            return l ? l.textContent.trim() : '';
        }

        function valorWidget(container, tipo) {
            if (tipo === 'stTextInput' || tipo === 'stNumberInput' || tipo === 'stTextArea') {
                var inp = container.querySelector('input, textarea');
                return inp ? inp.value : '';
            }
            if (tipo === 'stSelectbox') {
                var sel = container.querySelector('[data-baseweb="select"] [aria-selected="true"], ' +
                                                  '[data-baseweb="select"] span:first-child');
                return sel ? sel.textContent.trim() : '';
            }
            if (tipo === 'stMultiSelect') {
                var tags = container.querySelectorAll('[data-baseweb="tag"] span');
                if (!tags.length) return '(ninguno)';
                return Array.from(tags).map(function(t){ return t.textContent.trim(); })
                            .filter(Boolean).join(', ');
            }
            if (tipo === 'stSlider' || tipo === 'stSelectSlider') {
                var thumb = container.querySelector('[data-testid="stThumbValue"], [aria-valuenow]');
                if (thumb) return thumb.getAttribute('aria-valuenow') || thumb.textContent.trim();
            }
            if (tipo === 'stDateInput') {
                var di = container.querySelector('input');
                return di ? di.value : '';
            }
            if (tipo === 'stCheckbox') {
                var cb = container.querySelector('input[type="checkbox"]');
                return cb ? (cb.checked ? 'marcado OK' : 'desmarcado') : '';
            }
            return '';
        }

        function agGridInfo(mouseX, mouseY) {
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"], iframe[title*="aggrid"], iframe[title*="AgGrid"]');
            if (!frames.length) { frames = doc.querySelectorAll('iframe'); }
            for (var fi = 0; fi < frames.length; fi++) {
                var fr = frames[fi];
                var rect = fr.getBoundingClientRect();
                if (mouseX < rect.left || mouseX > rect.right ||
                    mouseY < rect.top  || mouseY > rect.bottom) continue;
                var fdoc = null;
                try { fdoc = fr.contentDocument; } catch(e) { continue; }
                if (!fdoc) continue;
                var rx = mouseX - rect.left;
                var ry = mouseY - rect.top;
                var inner = fdoc.elementFromPoint(rx, ry);
                if (!inner) continue;

                var cell = inner.closest('.ag-cell');
                if (cell) {
                    var colId   = cell.getAttribute('col-id') || '?';
                    var cellVal = cell.textContent.trim();
                    var row = cell.closest('.ag-row');
                    var rowIdx = row ? (row.getAttribute('row-index') || '?') : '?';
                    var rowTipo = '';
                    if (row) {
                        if (row.classList.contains('ag-row-pinned')) rowTipo = ' [TOTAL]';
                        else if (row.classList.contains('ag-row-group')) rowTipo = ' [grupo]';
                    }
                    return ['[tabla] AgGrid > celda',
                        '  columna : ' + colId,
                        '  valor   : ' + (cellVal.length > 60 ? cellVal.slice(0,57)+'...' : cellVal),
                        '  fila no : ' + rowIdx + rowTipo].join('\\n');
                }

                var hcell = inner.closest('.ag-header-cell');
                if (hcell) {
                    var hColId = hcell.getAttribute('col-id') || '?';
                    var hLabel = txt(hcell.querySelector('.ag-header-cell-text')) || hColId;
                    var sortIcon = hcell.querySelector('.ag-sort-ascending-icon:not(.ag-hidden)');
                    var sortDesc = hcell.querySelector('.ag-sort-descending-icon:not(.ag-hidden)');
                    var sortInfo = sortIcon ? ' ^ ascendente' : sortDesc ? ' v descendente' : ' sin orden';
                    var filtroActivo = hcell.querySelector('.ag-filter-active') ? ' [filtro] filtro activo' : '';
                    return ['[tabla] AgGrid > encabezado',
                        '  col-id  : ' + hColId,
                        '  nombre  : ' + hLabel,
                        '  orden   :' + sortInfo + filtroActivo].join('\\n');
                }

                var colItem = inner.closest('.ag-column-select-column');
                if (colItem) {
                    var colName = txt(colItem.querySelector('.ag-column-select-column-label')) || '?';
                    var visible = colItem.querySelector('input[type="checkbox"]');
                    var visStr  = visible ? (visible.checked ? 'visible OK' : 'oculta') : '?';
                    return ['[tabla] AgGrid > panel columnas',
                        '  columna : ' + colName,
                        '  estado  : ' + visStr].join('\\n');
                }

                var filtItem = inner.closest('.ag-filter-toolpanel-instance');
                if (filtItem) {
                    var filtName = txt(filtItem.querySelector('.ag-filter-toolpanel-instance-header-text')) || '?';
                    return ['[tabla] AgGrid > panel filtros', '  filtro  : ' + filtName].join('\\n');
                }

                var pag = inner.closest('.ag-paging-panel');
                if (pag) {
                    var pagTxt = pag.textContent.replace(/\\s+/g, ' ').trim();
                    return ['[tabla] AgGrid > paginacion', '  ' + pagTxt.slice(0, 80)].join('\\n');
                }

                var status = inner.closest('.ag-status-bar');
                if (status) {
                    return ['[tabla] AgGrid > barra de estado',
                        '  ' + status.textContent.replace(/\\s+/g, ' ').trim().slice(0, 80)].join('\\n');
                }

                var menuItem = inner.closest('.ag-menu-option');
                if (menuItem) {
                    return '[tabla] AgGrid > menu: ' + txt(menuItem.querySelector('.ag-menu-option-text'));
                }

                if (fdoc.querySelector('.ag-root-wrapper')) {
                    return '[tabla] AgGrid > zona: ' + (inner.className || inner.tagName).toString().slice(0, 60);
                }
            }
            return null;
        }

        var WIDGET_MAP = {
            'stTextInput':    { ico: '[input]',  tipo: 'text_input'    },
            'stNumberInput':  { ico: '[num]',  tipo: 'number_input'  },
            'stTextArea':     { ico: '[texto]',  tipo: 'text_area'     },
            'stSelectbox':    { ico: '[select]',  tipo: 'selectbox'     },
            'stMultiSelect':  { ico: '[multi]',  tipo: 'multiselect'   },
            'stSlider':       { ico: '[slider]',  tipo: 'slider'        },
            'stSelectSlider': { ico: '[slider]',  tipo: 'select_slider' },
            'stDateInput':    { ico: '[fecha]',  tipo: 'date_input'    },
            'stTimeInput':    { ico: '[hora]',  tipo: 'time_input'    },
            'stCheckbox':     { ico: '[check]',  tipo: 'checkbox'      },
        };

        function labelDe(el, mouseX, mouseY) {
            for (var testid in WIDGET_MAP) {
                var container = el.closest('[data-testid="' + testid + '"]');
                if (!container) continue;
                var meta  = WIDGET_MAP[testid];
                var lbl   = labelWidget(container);
                var val   = valorWidget(container, testid);
                var inp   = container.querySelector('input, select, textarea');
                var keyAt = inp ? (inp.getAttribute('aria-label') || inp.id || '') : '';
                if (/^st-[a-z0-9]+$/i.test(keyAt)) keyAt = '';
                var lines = [meta.ico + ' ' + meta.tipo];
                if (lbl)   lines.push('  label : ' + lbl);
                if (keyAt) lines.push('  key   : ' + keyAt);
                if (val)   lines.push('  valor : ' + (val.length > 55 ? val.slice(0,52)+'...' : val));
                return lines.join('\\n');
            }

            var btn = el.closest('[data-testid="baseButton-secondary"], [data-testid="baseButton-primary"], button[kind]');
            if (btn) {
                var btxt = btn.innerText.trim().replace(/\\n/g, ' ');
                var bkey = btn.getAttribute('data-testid') || '';
                var blines = ['[btn] button'];
                if (btxt) blines.push('  texto : ' + btxt);
                if (bkey && bkey !== 'baseButton-secondary' && bkey !== 'baseButton-primary')
                    blines.push('  testid: ' + bkey);
                return blines.join('\\n');
            }

            var popover = el.closest('[data-testid="stPopover"]');
            if (popover) {
                var pbtn = popover.querySelector('button');
                var ptxt = pbtn ? pbtn.innerText.trim() : '?';
                var popen = popover.querySelector('[data-testid="stPopoverBody"]') ? ' (abierto)' : ' (cerrado)';
                return '[pop] popover\\n  texto : ' + ptxt + '\\n  estado: ' + popen.trim();
            }

            var tabBtn = el.closest('[data-baseweb="tab"]');
            if (tabBtn) {
                var isActive = tabBtn.getAttribute('aria-selected') === 'true';
                return '[tab] tab\\n  nombre: ' + tabBtn.innerText.trim() +
                       '\\n  estado: ' + (isActive ? 'activa OK' : 'inactiva');
            }

            var expander = el.closest('[data-testid="stExpander"]');
            if (expander) {
                var etxt2 = expander.querySelector('summary p, summary span, .streamlit-expanderHeader p');
                var eopen = expander.querySelector('[data-testid="stExpanderDetails"]')
                var eIsOpen = eopen ? (eopen.style.display !== 'none' && eopen.style.visibility !== 'hidden') : false;
                return '[exp] expander\\n  titulo: ' + (etxt2 ? etxt2.textContent.trim() : '?') +
                       '\\n  estado: ' + (eIsOpen ? 'abierto' : 'cerrado');
            }

            var metric = el.closest('[data-testid="stMetric"]');
            if (metric) {
                var mlbl2  = metric.querySelector('[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"]');
                var mval   = metric.querySelector('[data-testid="stMetricValue"]');
                var mdelta = metric.querySelector('[data-testid="stMetricDelta"]');
                var mlines = ['[metric] metric'];
                if (mlbl2)  mlines.push('  label : ' + mlbl2.textContent.trim());
                if (mval)   mlines.push('  valor : ' + mval.textContent.trim());
                if (mdelta) mlines.push('  delta : ' + mdelta.textContent.trim());
                return mlines.join('\\n');
            }

            var plotly = el.closest('.js-plotly-plot, [data-testid="stPlotlyChart"]');
            if (plotly) {
                var ptitle2 = plotly.querySelector('.gtitle, .g-gtitle');
                var xTitle  = plotly.querySelector('.g-xtitle');
                var yTitle  = plotly.querySelector('.g-ytitle');
                var plines  = ['[chart] plotly'];
                plines.push('  titulo: ' + (ptitle2 ? ptitle2.textContent.trim() : '(sin titulo)'));
                if (xTitle) plines.push('  eje X : ' + xTitle.textContent.trim());
                if (yTitle) plines.push('  eje Y : ' + yTitle.textContent.trim());
                return plines.join('\\n');
            }

            var agEl = el.closest('[data-testid="stAgGrid"], .ag-root-wrapper');
            if (agEl || el.tagName === 'IFRAME') {
                var agInfo = agGridInfo(mouseX, mouseY);
                if (agInfo) return agInfo;
                return '[tabla] AgGrid tabla';
            }

            var railIcon = el.closest('.rail-icon');
            if (railIcon) {
                var rname   = railIcon.getAttribute('data-tooltip') || railIcon.innerText.trim();
                var rActive = railIcon.classList.contains('active');
                return '[nav] nav\\n  reporte: ' + rname + '\\n  estado : ' + (rActive ? 'activo OK' : 'inactivo');
            }

            var caption = el.closest('[data-testid="stCaptionContainer"]');
            if (caption) {
                return '[i] caption\\n  ' + caption.textContent.trim().slice(0, 80);
            }

            return null;
        }

        var elActual = null;
        function resaltarEl(el, etiqueta) {
            if (elActual) { elActual.style.outline = ''; elActual.style.outlineOffset = ''; }
            if (el && etiqueta) {
                el.style.outline = '2px solid var(--accent)';
                el.style.outlineOffset = '2px';
                elActual = el;
            } else { elActual = null; }
        }

        if (!win.__inspectorListeners) {
            win.__inspectorListeners = true;

            doc.addEventListener('mousemove', function(e) {
              try {
                var tip = doc.getElementById('el-inspector-tip');
                if (!tip) return;
                if (!inspectorActivo()) {
                    tip.style.opacity = '0';
                    resaltarEl(null, null);
                    return;
                }

                var el = e.target;
                var etiqueta = null;
                var cursor = el;

                var agInfo = null;
                try { agInfo = agGridInfo(e.clientX, e.clientY); } catch(err) { agInfo = null; }
                if (agInfo) {
                    etiqueta = agInfo;
                    var agFrame = doc.querySelector('iframe[src*="st_aggrid"], [data-testid="stAgGrid"] iframe');
                    if (!agFrame) {
                        var iframes = doc.querySelectorAll('iframe');
                        for (var fi=0; fi<iframes.length; fi++) {
                            var r = iframes[fi].getBoundingClientRect();
                            if (e.clientX >= r.left && e.clientX <= r.right &&
                                e.clientY >= r.top  && e.clientY <= r.bottom) {
                                agFrame = iframes[fi]; break;
                            }
                        }
                    }

                if (agFrame) resaltarEl(agFrame, etiqueta);
            } else {
                for (var i = 0; i < 12 && cursor && cursor !== doc.body; i++) {
                    try { etiqueta = labelDe(cursor, e.clientX, e.clientY); } catch(err) { etiqueta = null; }
                    if (etiqueta) { el = cursor; break; }
                    cursor = cursor.parentElement;
                }
                if (etiqueta) resaltarEl(el, etiqueta);
                else resaltarEl(null, null);
            }

            if (etiqueta) {
                tip.textContent = etiqueta;
                tip.style.opacity = '1';
                var x = e.clientX + 16;
                var y = e.clientY - 10;
                var tw = tip.offsetWidth  || 260;
                var th = tip.offsetHeight || 80;
                if (x + tw > win.innerWidth  - 8) x = e.clientX - tw - 16;
                if (y + th > win.innerHeight - 8) y = e.clientY - th - 10;
                if (y < 6) y = 6;
                tip.style.left = x + 'px';
                tip.style.top  = y + 'px';
            } else {
                tip.style.opacity = '0';
            }
              } catch(err) {
                if (win.__logErr) win.__logErr('Inspector mousemove: ' + err.message);
              }
            }, true);

            doc.addEventListener('mouseleave', function() {
                var tip = doc.getElementById('el-inspector-tip');
                if (tip) tip.style.opacity = '0';
                resaltarEl(null, null);
            });

            doc.addEventListener('keydown', function(e) {
                if (e.altKey && (e.key === 'i' || e.key === 'I')) {
                    var url = new URL(win.location.href);
                    if (url.searchParams.get('debug') === '1') {
                        url.searchParams.delete('debug');
                    } else {
                        url.searchParams.set('debug', '1');
                    }
                    win.history.replaceState({}, '', url.toString());
                    var badge = doc.getElementById('el-inspector-badge');
                    if (badge) badge.style.display = inspectorActivo() ? 'flex' : 'none';
                    if (!inspectorActivo()) {
                        var tip = doc.getElementById('el-inspector-tip');
                        if (tip) tip.style.opacity = '0';
                        resaltarEl(null, null);
                    }
                }
            });

            var _push = win.history.pushState.bind(win.history);
            win.history.pushState = function() { _push.apply(win.history, arguments); actualizarBadge(); };
            win.addEventListener('popstate', actualizarBadge);

        }

    })();
    </script>
    """, height=0, scrolling=False)


# ===========================================================================
# BARRA DE PAGINACION v2 (NUMEROS + SALTO)
# ===========================================================================

def inject_pagination_v2():
    """Barra de paginación personalizada con números y salto de página.

    NOTA — colores del bloque #pgv2:
        Se inyecta con agDoc.head.appendChild dentro del iframe de AgGrid.
        Antes usaba var(--x) del padre y no resolvía (botones sin fondo,
        número activo sin destacar, etc). Ahora usa el bloque pre-computado
        _PGV2_CSS_IFRAME con constantes de tema.py. Ver arquitectura.md §Fase 2.
    """
    pgv2_css_js = json.dumps(_PGV2_CSS_IFRAME)
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var tries = 0, MAX = 60;

      var PGV2_CSS = """ + pgv2_css_js + """;

      function intDe(txt){
        var m = (txt||'').match(/\\d[\\d.,]*/g);
        if (!m) return [];
        return m.map(function(s){ return parseInt(s.replace(/[^0-9]/g,''),10); })
                .filter(function(n){ return !isNaN(n); });
      }

      function leerEstado(panel){
        var desc = panel.querySelector('.ag-paging-description');
        var nums = desc ? intDe(desc.textContent) : [];
        if (nums.length >= 2) return { cur: nums[0], tot: nums[nums.length-1] };
        var c = panel.querySelector('[ref=lbCurrent]');
        var t = panel.querySelector('[ref=lbTotal]');
        if (c && t){
          var cc = intDe(c.textContent)[0], tt = intDe(t.textContent)[0];
          if (!isNaN(cc) && !isNaN(tt)) return { cur: cc, tot: tt };
        }
        return null;
      }

      function montar(agDoc){
        var panel = agDoc.querySelector('.ag-paging-panel');
        if (!panel) return 'sin-panel';
        var est = leerEstado(panel);
        if (!est) return 'sin-estado';

        if (!agDoc.getElementById('pgv2-css')){
          var stl = agDoc.createElement('style');
          stl.id = 'pgv2-css';
          stl.textContent = PGV2_CSS;
          agDoc.head.appendChild(stl);
        }

        function go(p){
          var e = leerEstado(panel); if (!e) return;
          p = Math.max(1, Math.min(e.tot, p));
          if (p === e.cur) return;
          win.__pgv2busy = true;
          /* AgGrid moderno usa data-ref; ref queda por compatibilidad. */
          var btn = (p > e.cur)
              ? panel.querySelector('[ref=btNext], [data-ref=btNext]')
              : panel.querySelector('[ref=btPrevious], [data-ref=btPrevious]');
          var n = Math.abs(p - e.cur);
          for (var k=0; k<n && btn; k++){ btn.click(); }
          win.__pgv2busy = false;
          render();
        }

        function paginas(c, t){
          var want = [1, t, c, c-1, c+1, c-2, c+2], seen = {}, arr = [];
          for (var i=0;i<want.length;i++){
            var v = want[i];
            if (v>=1 && v<=t && !seen[v]){ seen[v]=1; arr.push(v); }
          }
          arr.sort(function(a,b){ return a-b; });
          var out = [];
          for (var j=0;j<arr.length;j++){
            if (j>0 && arr[j]-arr[j-1] > 1) out.push('...');
            out.push(arr[j]);
          }
          return out;
        }

        function render(){
          var e = leerEstado(panel); if (!e) return;
          var c = e.cur, t = e.tot;
          /* Una sola página: nada que paginar; la barra completa se oculta
             y reaparece sola cuando el total de páginas vuelve a crecer
             (el MutationObserver re-invoca render en cada cambio). */
          panel.style.display = (t <= 1) ? 'none' : '';
          if (t <= 1) return;
          var bar = agDoc.getElementById('pgv2');
          if (!bar){ bar = agDoc.createElement('div'); bar.id = 'pgv2'; panel.appendChild(bar); }
          var html = '<span class="pgv2-pages">';
          html += '<button data-go="'+(c-1)+'" '+(c<=1?'disabled':'')+' aria-label="Anterior">\\u2039</button>';
          var ps = paginas(c, t);
          for (var i=0;i<ps.length;i++){
            if (ps[i]==='...') html += '<span class="pgv2-dots">\\u2026</span>';
            else html += '<button data-go="'+ps[i]+'" class="'+(ps[i]===c?'pgv2-on':'')+'">'+ps[i]+'</button>';
          }
          html += '<button data-go="'+(c+1)+'" '+(c>=t?'disabled':'')+' aria-label="Siguiente">\\u203a</button>';
          html += '</span>';
          html += '<span class="pgv2-jump">Ir a '+
                  '<input type="number" min="1" max="'+t+'" value="'+c+'" id="pgv2-in" aria-label="Ir a pagina">'+
                  '<button id="pgv2-goin" aria-label="Ir">\\u2192</button></span>';
          bar.innerHTML = html;

          var btns = bar.querySelectorAll('button[data-go]');
          for (var b=0;b<btns.length;b++){
            btns[b].addEventListener('click', function(){
              var v = parseInt(this.getAttribute('data-go'),10);
              if (!isNaN(v)) go(v);
            });
          }
          var inp = bar.querySelector('#pgv2-in');
          var goin = bar.querySelector('#pgv2-goin');
          function jump(){ var v = parseInt(inp.value,10); if (!isNaN(v)) go(v); }
          goin.addEventListener('click', jump);
          inp.addEventListener('keydown', function(ev){
            if (ev.key === 'Enter'){ ev.preventDefault(); jump(); }
          });
        }

        win.__pgv2render = render;
        if (!panel.__pgv2obs){
          var diana = panel.querySelector('.ag-paging-description') || panel;
          var obs = new win.MutationObserver(function(){
            if (!win.__pgv2busy && win.__pgv2render) win.__pgv2render();
          });
          obs.observe(diana, {childList:true, characterData:true, subtree:true});
          panel.__pgv2obs = obs;
        }

        render();
        return 'ok';
      }

      function buscarFrames(){
        var f = doc.querySelectorAll('iframe[src*="st_aggrid"]');
        if (f.length) return f;
        return doc.querySelectorAll('iframe');
      }

      function check(){
        tries++;
        var frames = buscarFrames();
        var ultimo = 'sin-iframe';
        for (var i=0;i<frames.length;i++){
          var d = null;
          try { d = frames[i].contentDocument; } catch(e){}
          if (!d || !d.querySelector('.ag-paging-panel')) continue;
          var r = montar(d);
          if (r === 'ok') return;
          ultimo = r;
        }
        if (tries < MAX){ win.setTimeout(check, 500); return; }
        if (win.__logErr) win.__logErr('Paginacion v2 no se pudo montar (' + ultimo + ').');
      }
      win.setTimeout(check, 800);
    })();
    </script>
    """, height=0)


# ===========================================================================
# BOTÓN MAXIMIZAR AGGRID — TODOS LOS REPORTES (NUEVA VERSIÓN CON FULLSCREEN API)
# ===========================================================================

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


# ===========================================================================
# ALTURA DINÁMICA DEL GRID — llena el alto de pantalla disponible
# ===========================================================================

def inject_dynamic_grid_height(offset_px: int = 260, min_px: int = 320):
    """
    Estira la tabla AgGrid para que ocupe el alto de pantalla disponible,
    en lugar del height=... fijo con el que se renderiza.

    DISEÑO SEGURO (mismo espíritu que inject_maximize_aggrid):
    - El grid se sigue creando con su height fijo en tablas.py. Esta función
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


# ===========================================================================
# FIX: PANEL COLUMNAS DE AJUSTE DE INVENTARIO — reposicionamiento dinámico
# ===========================================================================

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


# ===========================================================================
# ALINEAR TÍTULO + PESTAÑAS DE AJUSTE CON EL BORDE DE LA TABLA
# ===========================================================================

def inject_alinear_cabecera_ajuste():
    """
    Alinea el título "Ajuste de Inventario" y las pestañas Tabla/Gráficos
    (ambos position:fixed, ver estilos.py) con el borde izquierdo REAL de
    la tabla AgGrid — no con el contenedor de contenido, que empieza justo
    tras el riel y queda más a la izquierda que la tabla.

    Por qué JS y no un valor fijo en CSS: el título/pestañas están fuera
    del flujo normal (position:fixed) mientras que la tabla vive dentro del
    padding de Streamlit, que varía con el ancho de ventana. En vez de
    adivinar píxeles, se mide el iframe de AgGrid con
    getBoundingClientRect() y se aplica como left inline. Mientras el
    iframe no exista aún, cae al borde del contenedor como aproximación.

    Mismo espíritu que inject_dynamic_grid_height: medición puntual con
    reintentos hasta que los elementos existan, SIN listener de resize
    continuo (evita el bucle de re-medición / error React #185).
    """
    components.html("""
    <script>
    (function(){
        var win = window.parent, doc = win.document;
        var tries = 0, MAX = 40;

        function bordeTabla() {
            /* Borde izquierdo del iframe de AgGrid (la tabla visible). */
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"]');
            for (var i = 0; i < frames.length; i++) {
                var r = frames[i].getBoundingClientRect();
                if (r.width > 0) return r.left;
            }
            /* Aún no montó: aproximar con el contenedor de contenido. */
            var contenido = doc.querySelector('[data-testid="stMainBlockContainer"]')
                          || doc.querySelector('.block-container');
            return contenido ? contenido.getBoundingClientRect().left : null;
        }

        function alinear() {
            var titulo = doc.querySelector('.titulo-ajuste-reporte');
            var left = bordeTabla();
            if (left === null || !titulo) return false;

            titulo.style.setProperty('left', left + 'px', 'important');

            var tabs = doc.querySelector('.st-key-ajuste_tabs_top');
            if (tabs) tabs.style.setProperty('left', left + 'px', 'important');

            return true;
        }

        function check() {
            tries++;
            alinear();
            if (tries < MAX) win.setTimeout(check, 400);
        }
        win.setTimeout(check, 300);
    })();
    </script>
    """, height=0)
