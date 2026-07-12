"""
Inyecciones de HTML/JS en la página: overlay de errores, health-check
del grid de AgGrid, botón flotante del sidebar e inspector de elementos.
"""

import streamlit as st
import streamlit.components.v1 as components


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


def inject_grid_health_check():
    """Comprueba que el grid de AgGrid se haya montado de verdad e inyecta
    CSS de paginación directamente dentro del iframe para garantizar que los
    estilos pisen los del tema nativo (balham/material).

    Los errores de render DENTRO del iframe de AgGrid (p.ej. un cellRenderer/
    JsCode que devuelve un nodo DOM → React #31) no llegan a la ventana
    principal, así que aquí inspeccionamos el iframe: si existe pero no aparece
    '.ag-root-wrapper' tras unos segundos, lo reportamos al overlay de errores.
    (No revisa el nº de filas: un grid vacío legítimo SÍ monta el wrapper.)"""
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var tries = 0, MAX = 50;

      var PAG_CSS = [
        '.ag-status-bar {',
        '  background: var(--bg-primary) !important;',
        '  border-top: 1px solid var(--border) !important;',
        '  color: var(--text-secondary) !important;',
        '  padding: 4px 16px !important;',
        '  font-size: 12px !important;',
        '  background-image: none !important;',
        '  background-color: var(--bg-primary) !important;',
        '}',
        '.ag-status-bar * {',
        '  background-image: none !important;',
        '}',
        '.ag-status-name-value { color: var(--text-secondary) !important; font-size: 12px !important; }',
        '.ag-status-name-value-value { color: var(--text-primary) !important; font-weight: 600 !important; }',

        '.ag-paging-panel {',
        '  display: flex !important;',
        '  align-items: center !important;',
        '  justify-content: space-between !important;',
        '  background: var(--bg-primary) !important;',
        '  background-image: none !important;',
        '  border: 1px solid var(--border) !important;',
        '  border-radius: 12px !important;',
        '  margin-top: 12px !important;',
        '  padding: 8px 16px !important;',
        '  min-height: 44px !important;',
        '  font-size: 12px !important;',
        '  color: var(--icon-muted) !important;',
        '}',

        '.ag-paging-page-size { order: -1 !important; margin-right: auto !important; }',
        '.ag-paging-page-size .ag-label { color: var(--icon-muted) !important; font-size: 12px !important; margin-right: 6px !important; }',
        '.ag-paging-page-size .ag-select, .ag-paging-page-size select {',
        '  border: 1px solid var(--border) !important;',
        '  border-radius: 6px !important;',
        '  background: #fff !important;',
        '  color: var(--text-primary) !important;',
        '  font-size: 12px !important;',
        '  padding: 2px 6px !important;',
        '}',

        '.ag-paging-row-summary-panel { color: var(--icon-muted) !important; font-size: 12px !important; }',
        '.ag-paging-row-summary-panel-number { color: var(--text-primary) !important; font-weight: 600 !important; }',

        '.ag-paging-description { color: var(--icon-muted) !important; font-size: 12px !important; }',

        '.ag-paging-button {',
        '  width: 28px !important; height: 28px !important;',
        '  border: 1px solid var(--border) !important;',
        '  border-radius: 6px !important;',
        '  background: #fff !important;',
        '  color: var(--text-secondary) !important;',
        '  font-size: 14px !important;',
        '  margin: 0 2px !important;',
        '  cursor: pointer !important;',
        '  display: inline-flex !important;',
        '  align-items: center !important;',
        '  justify-content: center !important;',
        '  transition: all 0.15s ease !important;',
        '  position: relative !important;',
        '}',
        '.ag-paging-button span, .ag-paging-button .ag-icon {',
        '  display: none !important;',
        '}',
        '.ag-paging-button[ref="btFirst"]::after  { content: "«" !important; }',
        '.ag-paging-button[ref="btPrevious"]::after { content: "‹" !important; }',
        '.ag-paging-button[ref="btNext"]::after   { content: "›" !important; }',
        '.ag-paging-button[ref="btLast"]::after   { content: "»" !important; }',
        '.ag-paging-button::after {',
        '  font-size: 16px !important;',
        '  line-height: 1 !important;',
        '  color: var(--text-secondary) !important;',
        '}',
        '.ag-paging-button:hover:not(.ag-disabled) {',
        '  background: var(--accent-tint) !important;',
        '  border-color: var(--focus-lavender) !important;',
        '}',
        '.ag-paging-button:hover:not(.ag-disabled)::after {',
        '  color: var(--accent-hover) !important;',
        '}',
        '.ag-paging-button.ag-disabled {',
        '  border-color: var(--line-soft) !important;',
        '  background: var(--bg-primary) !important;',
        '  cursor: default !important;',
        '  opacity: 0.4 !important;',
        '}',

        '.ag-filter-toolpanel {',
        '  border: none !important;',
        '  border-radius: 0 !important;',
        '  margin: 0 !important;',
        '  overflow-y: auto !important;',
        '  overflow-x: hidden !important;',
        '}',
        '.ag-filter-toolpanel::-webkit-scrollbar { width: 8px; }',
        '.ag-filter-toolpanel::-webkit-scrollbar-track { background: transparent; }',
        '.ag-filter-toolpanel::-webkit-scrollbar-thumb { background: var(--scroll-thumb); border-radius: 4px; }',
      ].join('\\n');

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
# BOTÓN FLOTANTE PARA ABRIR/CERRAR EL SIDEBAR (CACHEADO)
# ===========================================================================

@st.cache_data
def get_sidebar_toggle_html():
    """Retorna el HTML del botón flotante (cacheado)."""
    return """
    <script>
    (function () {
        const doc = window.parent.document;
        const BTN_ID = 'mi-toggle-sidebar';

        function buscarControlNativo() {
            const sels = [
                '[data-testid="stSidebarCollapseButton"] button',
                '[data-testid="stSidebarCollapseButton"]',
                '[data-testid="stExpandSidebarButton"]',
                '[data-testid="collapsedControl"]',
                '[data-testid="stSidebarCollapsedControl"]',
                'button[kind="header"]',
                'section[data-testid="stSidebar"] button'
            ];
            for (const s of sels) {
                const el = doc.querySelector(s);
                if (el) return el;
            }
            return null;
        }

        function sidebarEstaAbierto() {
            const sb = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sb) return false;
            const rect = sb.getBoundingClientRect();
            return rect.left > -100;
        }

        function toggleSidebar() {
            const nativo = buscarControlNativo();
            if (nativo) { nativo.click(); return; }

            const sb = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sb) return;

            if (sidebarEstaAbierto()) {
                sb.style.transform = 'translateX(-110%)';
                sb.style.width = '0';
                sb.style.minWidth = '0';
                sb.style.overflow = 'hidden';
                sb.dataset.abierto = '';
            } else {
                sb.style.transform = 'none';
                sb.style.width = '21rem';
                sb.style.minWidth = '21rem';
                sb.style.visibility = 'visible';
                sb.style.overflow = 'visible';
                sb.style.zIndex = '1000';
                sb.dataset.abierto = '1';
            }
        }

        function asegurarBoton() {
            if (doc.getElementById(BTN_ID)) return;
            const b = doc.createElement('button');
            b.id = BTN_ID;
            b.innerHTML = '☰';
            b.title = 'Abrir / cerrar menú';
            b.style.cssText = [
                'position:fixed', 'top:12px', 'left:12px', 'z-index:1000000',
                'width:44px', 'height:44px', 'border-radius:10px',
                'border:1px solid var(--accent-hover)', 'background:var(--accent)', 'color:var(--bg-secondary)',
                'font-size:20px', 'line-height:1', 'cursor:pointer',
                'box-shadow:0 2px 8px rgba(0,0,0,0.2)', 'display:flex',
                'align-items:center', 'justify-content:center', 'padding:0'
            ].join(';');
            b.onclick = toggleSidebar;
            doc.body.appendChild(b);
        }

        asegurarBoton();
        setInterval(asegurarBoton, 1000);
    })();
    </script>
    """


def inject_sidebar_toggle():
    """Inyecta el botón flotante cacheado."""
    components.html(get_sidebar_toggle_html(), height=0)


# ===========================================================================
# INSPECTOR DE ELEMENTOS — tooltips de identificación para capturas de pantalla
# ===========================================================================

def inject_element_inspector():
    """
    Inspector de elementos v2 - tooltip enriquecido al pasar el cursor.
    Activacion : ?debug=1 en la URL  o  Alt+I

    Unificado con el resto de herramientas de desarrollo: el mismo ?debug=1
    que muestra el panel de diagnostico activa tambien este inspector.
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
                        '  fila no : ' + rowIdx + rowTipo].join('\n');
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
                        '  orden   :' + sortInfo + filtroActivo].join('\n');
                }

                var colItem = inner.closest('.ag-column-select-column');
                if (colItem) {
                    var colName = txt(colItem.querySelector('.ag-column-select-column-label')) || '?';
                    var visible = colItem.querySelector('input[type="checkbox"]');
                    var visStr  = visible ? (visible.checked ? 'visible OK' : 'oculta') : '?';
                    return ['[tabla] AgGrid > panel columnas',
                        '  columna : ' + colName,
                        '  estado  : ' + visStr].join('\n');
                }

                var filtItem = inner.closest('.ag-filter-toolpanel-instance');
                if (filtItem) {
                    var filtName = txt(filtItem.querySelector('.ag-filter-toolpanel-instance-header-text')) || '?';
                    return ['[tabla] AgGrid > panel filtros', '  filtro  : ' + filtName].join('\n');
                }

                var pag = inner.closest('.ag-paging-panel');
                if (pag) {
                    var pagTxt = pag.textContent.replace(/\s+/g, ' ').trim();
                    return ['[tabla] AgGrid > paginacion', '  ' + pagTxt.slice(0, 80)].join('\n');
                }

                var status = inner.closest('.ag-status-bar');
                if (status) {
                    return ['[tabla] AgGrid > barra de estado',
                        '  ' + status.textContent.replace(/\s+/g, ' ').trim().slice(0, 80)].join('\n');
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
                return lines.join('\n');
            }

            var btn = el.closest('[data-testid="baseButton-secondary"], [data-testid="baseButton-primary"], button[kind]');
            if (btn) {
                var btxt = btn.innerText.trim().replace(/\n/g, ' ');
                var bkey = btn.getAttribute('data-testid') || '';
                var blines = ['[btn] button'];
                if (btxt) blines.push('  texto : ' + btxt);
                if (bkey && bkey !== 'baseButton-secondary' && bkey !== 'baseButton-primary')
                    blines.push('  testid: ' + bkey);
                return blines.join('\n');
            }

            var popover = el.closest('[data-testid="stPopover"]');
            if (popover) {
                var pbtn = popover.querySelector('button');
                var ptxt = pbtn ? pbtn.innerText.trim() : '?';
                var popen = popover.querySelector('[data-testid="stPopoverBody"]') ? ' (abierto)' : ' (cerrado)';
                return '[pop] popover\n  texto : ' + ptxt + '\n  estado: ' + popen.trim();
            }

            var tabBtn = el.closest('[data-baseweb="tab"]');
            if (tabBtn) {
                var isActive = tabBtn.getAttribute('aria-selected') === 'true';
                return '[tab] tab\n  nombre: ' + tabBtn.innerText.trim() +
                       '\n  estado: ' + (isActive ? 'activa OK' : 'inactiva');
            }

            var expander = el.closest('[data-testid="stExpander"]');
            if (expander) {
                var etxt2 = expander.querySelector('summary p, summary span, .streamlit-expanderHeader p');
                var eopen = expander.querySelector('[data-testid="stExpanderDetails"]')
                var eIsOpen = eopen ? (eopen.style.display !== 'none' && eopen.style.visibility !== 'hidden') : false;
                return '[exp] expander\n  titulo: ' + (etxt2 ? etxt2.textContent.trim() : '?') +
                       '\n  estado: ' + (eIsOpen ? 'abierto' : 'cerrado');
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
                return mlines.join('\n');
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
                return plines.join('\n');
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
                return '[nav] nav\n  reporte: ' + rname + '\n  estado : ' + (rActive ? 'activo OK' : 'inactivo');
            }

            var caption = el.closest('[data-testid="stCaptionContainer"]');
            if (caption) {
                return '[i] caption\n  ' + caption.textContent.trim().slice(0, 80);
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
    """Barra de paginación personalizada con números y salto de página."""
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var tries = 0, MAX = 60;

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
          stl.textContent =
            '.ag-paging-panel{position:relative!important;justify-content:center!important;}'+
            '.ag-paging-panel .ag-paging-page-size{position:absolute!important;left:16px!important;'+
            'top:50%!important;transform:translateY(-50%)!important;margin:0!important;}'+
            '.ag-paging-panel .ag-paging-row-summary-panel,'+
            '.ag-paging-description,'+
            '.ag-paging-button{'+
            'position:absolute!important;left:-9999px!important;width:1px!important;'+
            'height:1px!important;overflow:hidden!important;}'+
            '#pgv2{display:inline-flex;align-items:center;gap:14px;margin:0 auto;'+
            'font:13px -apple-system,BlinkMacSystemFont,sans-serif;color:var(--icon-muted);}'+
            '#pgv2 .pgv2-pages{display:inline-flex;align-items:center;gap:6px;}'+
            '#pgv2 button{min-width:30px;height:30px;padding:0 8px;border:1px solid var(--border);'+
            'border-radius:8px;background:#fff;color:var(--text-secondary);font-size:13px;cursor:pointer;'+
            'display:inline-flex;align-items:center;justify-content:center;transition:all .15s;}'+
            '#pgv2 button:hover:not(:disabled){background:var(--accent-tint);border-color:var(--focus-lavender);color:var(--accent-hover);}'+
            '#pgv2 button:disabled{opacity:.4;cursor:default;}'+
            '#pgv2 button.pgv2-on{background:var(--accent-hover);border-color:var(--accent-hover);color:#fff;font-weight:500;}'+
            '#pgv2 .pgv2-dots{color:var(--text-muted);padding:0 2px;}'+
            '#pgv2 .pgv2-jump{display:inline-flex;align-items:center;gap:7px;color:var(--text-secondary);}'+
            '#pgv2 .pgv2-jump input{width:48px;height:30px;border:1px solid var(--border);'+
            'border-radius:8px;text-align:center;color:var(--text-primary);font-size:13px;background:#fff;'+
            'outline:none;-moz-appearance:textfield;}'+
            '#pgv2 .pgv2-jump input:focus{border-color:var(--accent-hover);box-shadow:0 0 0 2px var(--accent-light);}'+
            '#pgv2 .pgv2-jump input::-webkit-outer-spin-button,'+
            '#pgv2 .pgv2-jump input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0;}';
          agDoc.head.appendChild(stl);
        }

        function go(p){
          var e = leerEstado(panel); if (!e) return;
          p = Math.max(1, Math.min(e.tot, p));
          if (p === e.cur) return;
          win.__pgv2busy = true;
          var btn = (p > e.cur) ? panel.querySelector('[ref=btNext]')
                                : panel.querySelector('[ref=btPrevious]');
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
          var bar = agDoc.getElementById('pgv2');
          if (!bar){ bar = agDoc.createElement('div'); bar.id = 'pgv2'; panel.appendChild(bar); }
          var html = '<span class="pgv2-pages">';
          html += '<button data-go="'+(c-1)+'" '+(c<=1?'disabled':'')+' aria-label="Anterior">\u2039</button>';
          var ps = paginas(c, t);
          for (var i=0;i<ps.length;i++){
            if (ps[i]==='...') html += '<span class="pgv2-dots">\u2026</span>';
            else html += '<button data-go="'+ps[i]+'" class="'+(ps[i]===c?'pgv2-on':'')+'">'+ps[i]+'</button>';
          }
          html += '<button data-go="'+(c+1)+'" '+(c>=t?'disabled':'')+' aria-label="Siguiente">\u203a</button>';
          html += '</span>';
          html += '<span class="pgv2-jump">Ir a '+
                  '<input type="number" min="1" max="'+t+'" value="'+c+'" id="pgv2-in" aria-label="Ir a pagina">'+
                  '<button id="pgv2-goin" aria-label="Ir">\u2192</button></span>';
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
    """
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
                s.textContent = [
                    'html.fs-activo, html.fs-activo body {',
                    '  margin: 0 !important;',
                    '  height: 100vh !important;',
                    '  min-height: 100vh !important;',
                    '  max-height: 100vh !important;',
                    '  overflow: hidden !important;',
                    '}',
                    'html.fs-activo #root {',
                    '  height: 100vh !important;',
                    '  overflow: hidden !important;',
                    '}',
                    'html.fs-activo #root > div {',
                    '  height: 100vh !important;',
                    '}',
                    'html.fs-activo #root [class*="ag-theme-"]:not(.ag-dnd-ghost):not(.ag-popup) {',
                    '  height: 100vh !important;',
                    '}',
                    'html.fs-activo .ag-dnd-ghost,',
                    'html.fs-activo .ag-popup,',
                    'html.fs-activo body > [class*="ag-theme-"]:not(#gridContainer) {',
                    '  height: auto !important;',
                    '  min-height: 0 !important;',
                    '}',
                    'html.fs-activo .ag-root-wrapper {',
                    '  height: 100% !important; border-radius: 0 !important;',
                    '}',
                    'html.fs-activo .ag-column-panel,',
                    'html.fs-activo .ag-filter-toolpanel {',
                    '  height: 100% !important; overflow-y: auto !important;',
                    '}',
                    'html.fs-activo .ag-column-drop-vertical {',
                    '  flex: 0 0 auto !important;',
                    '  min-height: 3.2em !important;',
                    '}',
                    /* ── NUEVO: ⛶ integrado en el riel de pestañas ── */
                    '#' + BTN_ID + ' {',
                    '  width: 100%;',
                    '  height: 40px;',
                    '  border: none;',
                    '  border-bottom: 1px solid var(--border);',
                    '  background: transparent;',
                    '  color: var(--text-secondary);',
                    '  font-size: 16px;',
                    '  cursor: pointer;',
                    '  display: flex;',
                    '  align-items: center;',
                    '  justify-content: center;',
                    '  writing-mode: horizontal-tb;',
                    '  line-height: 1;',
                    '  transition: background .15s, color .15s;',
                    '}',
                    '#' + BTN_ID + ':hover {',
                    '  background: var(--accent-tint);',
                    '  color: var(--accent-hover);',
                    '}',
                    /* En fullscreen ocultamos el ⛶ (ya hay ✕ de salida). */
                    'html.fs-activo #' + BTN_ID + ' { display: none; }',
                    /* ── Botón de salida ✕ (idéntico al de antes) ── */
                    '#' + EXIT_ID + ' {',
                    '  position: fixed;',
                    '  top: 12px;',
                    '  right: 44px;',
                    '  z-index: 99999;',
                    '  width: 30px;',
                    '  height: 30px;',
                    '  border: 1px solid var(--text-secondary);',
                    '  border-radius: 6px;',
                    '  background: var(--text-primary);',
                    '  color: var(--bg-primary);',
                    '  font-size: 14px;',
                    '  cursor: pointer;',
                    '  display: none;',
                    '  align-items: center;',
                    '  justify-content: center;',
                    '  line-height: 1;',
                    '}',
                    'html.fs-activo #' + EXIT_ID + ' { display: flex; }',
                    '#' + EXIT_ID + ':hover { background: var(--exit-hover); }',
                ].join('\\n');
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

def inject_dynamic_grid_height(offset_px: int = 220, min_px: int = 480):
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

        function buscarIframe() {
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"]');
            if (!frames.length) frames = doc.querySelectorAll('iframe');
            for (var i = 0; i < frames.length; i++) {
                try {
                    var d = frames[i].contentDocument;
                    if (d && d.querySelector('.ag-root-wrapper')) return d;
                } catch(e) {}
            }
            return null;
        }

        function check() {
            tries++;
            var fdoc = buscarIframe();
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
