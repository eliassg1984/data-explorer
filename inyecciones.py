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
        if (esRuidoExterno(m)) return;   // ignorar ruido de extensiones
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
      var tries = 0, MAX = 20;

      var PAG_CSS = [
        '.ag-status-bar {',
        '  background: #f8fafc !important;',
        '  border-top: 1px solid #e2e8f0 !important;',
        '  color: #475569 !important;',
        '  padding: 4px 16px !important;',
        '  font-size: 12px !important;',
        '  background-image: none !important;',
        '  background-color: #f8fafc !important;',
        '}',
        '.ag-status-bar * {',
        '  background-image: none !important;',
        '}',
        '.ag-status-name-value { color: #475569 !important; font-size: 12px !important; }',
        '.ag-status-name-value-value { color: #1e293b !important; font-weight: 600 !important; }',

        '.ag-paging-panel {',
        '  display: flex !important;',
        '  align-items: center !important;',
        '  justify-content: space-between !important;',
        '  background: #f8fafc !important;',
        '  background-image: none !important;',
        '  border-top: 1px solid #e2e8f0 !important;',
        '  padding: 8px 16px !important;',
        '  min-height: 44px !important;',
        '  font-size: 12px !important;',
        '  color: #64748b !important;',
        '}',

        '.ag-paging-page-size { order: -1 !important; margin-right: auto !important; }',
        '.ag-paging-page-size .ag-label { color: #64748b !important; font-size: 12px !important; margin-right: 6px !important; }',
        '.ag-paging-page-size .ag-select, .ag-paging-page-size select {',
        '  border: 1px solid #e2e8f0 !important;',
        '  border-radius: 6px !important;',
        '  background: #fff !important;',
        '  color: #1e293b !important;',
        '  font-size: 12px !important;',
        '  padding: 2px 6px !important;',
        '}',

        '.ag-paging-row-summary-panel { color: #64748b !important; font-size: 12px !important; }',
        '.ag-paging-row-summary-panel-number { color: #1e293b !important; font-weight: 600 !important; }',

        '.ag-paging-description { color: #64748b !important; font-size: 12px !important; }',

        '.ag-paging-button {',
        '  width: 28px !important; height: 28px !important;',
        '  border: 1px solid #e2e8f0 !important;',
        '  border-radius: 6px !important;',
        '  background: #fff !important;',
        '  color: #475569 !important;',
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
        '  color: #475569 !important;',
        '}',
        '.ag-paging-button:hover:not(.ag-disabled) {',
        '  background: #eff6ff !important;',
        '  border-color: #93c5fd !important;',
        '}',
        '.ag-paging-button:hover:not(.ag-disabled)::after {',
        '  color: #2563eb !important;',
        '}',
        '.ag-paging-button.ag-disabled {',
        '  border-color: #f1f5f9 !important;',
        '  background: #f8fafc !important;',
        '  cursor: default !important;',
        '  opacity: 0.4 !important;',
        '}',

        '.ag-side-bar {',
        '  flex-direction: column !important;',
        '}',
        '.ag-side-bar .ag-side-buttons {',
        '  order: -1 !important;',
        '  flex: 0 0 auto !important;',
        '  display: flex !important;',
        '  flex-direction: row !important;',
        '  width: 100% !important;',
        '  border-right: none !important;',
        '  border-bottom: 1px solid #e2e8f0 !important;',
        '  padding: 0 !important;',
        '}',
        '.ag-side-bar .ag-tool-panel-wrapper {',
        '  order: 1 !important;',
        '  width: 100% !important;',
        '  flex: 1 1 auto !important;',
        '  height: auto !important;',
        '  min-height: 220px !important;',
        '}',
        '.ag-side-bar .ag-column-panel, .ag-side-bar .ag-column-select, .ag-side-bar .ag-filter-toolpanel {',
        '  flex: 1 1 auto !important;',
        '  height: auto !important;',
        '}',
        '.ag-side-bar .ag-side-button {',
        '  flex: 1 1 0 !important;',
        '  border-bottom: none !important;',
        '  border-right: 1px solid #e2e8f0 !important;',
        '}',
        '.ag-side-bar .ag-side-button:last-child {',
        '  border-right: none !important;',
        '}',
        '.ag-side-bar .ag-side-button-button {',
        '  writing-mode: horizontal-tb !important;',
        '  -webkit-writing-mode: horizontal-tb !important;',
        '  transform: none !important;',
        '  rotate: none !important;',
        '  display: flex !important;',
        '  flex-direction: row !important;',
        '  align-items: center !important;',
        '  justify-content: center !important;',
        '  width: 100% !important;',
        '  height: auto !important;',
        '  padding: 9px 6px !important;',
        '  gap: 6px !important;',
        '}',
        '.ag-side-bar .ag-side-button-label {',
        '  writing-mode: horizontal-tb !important;',
        '  -webkit-writing-mode: horizontal-tb !important;',
        '  transform: none !important;',
        '  rotate: none !important;',
        '  margin: 0 !important;',
        '  padding: 0 !important;',
        '  white-space: nowrap !important;',
        '  font-size: 12px !important;',
        '}',
        '.ag-side-bar .ag-side-button-icon-wrapper {',
        '  margin: 0 !important;',
        '  padding: 0 !important;',
        '}',

        '.ag-filter-toolpanel {',
        '  border: 1px solid #3b82f6 !important;',
        '  border-radius: 8px !important;',
        '  margin: 8px !important;',
        '  overflow: hidden !important;',
        '}',
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
        if (montado) return;
        if (tries < MAX){ setTimeout(check, 500); return; }
        if (win.__logErr) win.__logErr('Tabla no renderizada: el grid de AgGrid '
          + 'no se montó (posible cellRenderer/JsCode que devuelve un nodo DOM → React #31).');
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
                'border:1px solid #2563eb', 'background:#3b82f6', 'color:#ffffff',
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

        // NOTA: NO salimos temprano con un guard global. Si lo hicieramos, en
        // un rerender de Streamlit (que recrea el body) el tooltip se perderia
        // y no se volveria a crear -> el inspector "dejaba de funcionar". En su
        // lugar: el tip/badge se recrean si faltan (abajo), y los listeners se
        // registran una sola vez con su propia bandera (__inspectorListeners).

        function inspectorActivo() {
            return new URL(win.location.href).searchParams.get('debug') === '1';
        }

        // Reutiliza el tooltip si ya existe (un rerender de Streamlit puede
        // recrear el body); si no, lo crea. Asi nunca se pierde.
        var tip = doc.getElementById('el-inspector-tip');
        if (!tip) {
            tip = doc.createElement('div');
            tip.id = 'el-inspector-tip';
            tip.style.cssText = [
                'position:fixed',
                'pointer-events:none',
                'z-index:2147483647',
                'background:#0f172a',
                'color:#e2e8f0',
                'font:12px/1.55 "Courier New",monospace',
                'padding:7px 11px',
                'border-radius:6px',
                'border:1px solid #3b82f6',
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
                'background:#1e40af','color:#fff',
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
                var eopen = expander.querySelector('[data-testid="stExpanderDetails"]');
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
                el.style.outline = '2px solid #3b82f6';
                el.style.outlineOffset = '2px';
                elActual = el;
            } else { elActual = null; }
        }

        // -- Registrar los listeners UNA SOLA VEZ --------------------------
        // Persisten en `doc`/`win` entre rerenders, asi que con la bandera
        // basta. (El tip/badge si se recrean arriba en cada ejecucion.)
        if (!win.__inspectorListeners) {
            win.__inspectorListeners = true;

        doc.addEventListener('mousemove', function(e) {
          try {
            // Buscar el tooltip fresco (un rerender pudo recrearlo).
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

        }  // fin del guard __inspectorListeners

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
            '.ag-paging-panel .ag-paging-description,'+
            '.ag-paging-panel .ag-paging-button{'+
            'position:absolute!important;left:-9999px!important;width:1px!important;'+
            'height:1px!important;overflow:hidden!important;}'+
            '#pgv2{display:inline-flex;align-items:center;gap:14px;margin:0 auto;'+
            'font:13px -apple-system,BlinkMacSystemFont,sans-serif;color:#64748b;}'+
            '#pgv2 .pgv2-pages{display:inline-flex;align-items:center;gap:6px;}'+
            '#pgv2 button{min-width:30px;height:30px;padding:0 8px;border:1px solid #e2e8f0;'+
            'border-radius:8px;background:#fff;color:#475569;font-size:13px;cursor:pointer;'+
            'display:inline-flex;align-items:center;justify-content:center;transition:all .15s;}'+
            '#pgv2 button:hover:not(:disabled){background:#eff6ff;border-color:#93c5fd;color:#2563eb;}'+
            '#pgv2 button:disabled{opacity:.4;cursor:default;}'+
            '#pgv2 button.pgv2-on{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:500;}'+
            '#pgv2 .pgv2-dots{color:#94a3b8;padding:0 2px;}'+
            '#pgv2 .pgv2-jump{display:inline-flex;align-items:center;gap:7px;color:#475569;}'+
            '#pgv2 .pgv2-jump input{width:48px;height:30px;border:1px solid #e2e8f0;'+
            'border-radius:8px;text-align:center;color:#1e293b;font-size:13px;background:#fff;'+
            'outline:none;-moz-appearance:textfield;}'+
            '#pgv2 .pgv2-jump input:focus{border-color:#2563eb;box-shadow:0 0 0 2px #dbeafe;}'+
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
# BOTÓN MAXIMIZAR AGGRID — TODOS LOS REPORTES
# ===========================================================================

def inject_maximize_aggrid():
    """
    Inyecta un botón flotante en posición fija (esquina superior derecha)
    que pone la tabla AgGrid en pantalla completa.
    """
    components.html("""
    <script>
    (function(){
        var win = window.parent;
        var doc = win.document;
        var BTN_ID = 'aggrid-maximize-btn';
        var maximizado = false;
        var estilosOriginales = {};
        var tries = 0;
        var MAX = 40;

        // ── CSS del botón flotante ───────────────────────────────────────
        function inyectarCSS() {
            if (doc.getElementById('aggrid-max-css')) return;
            var s = doc.createElement('style');
            s.id = 'aggrid-max-css';
            s.textContent = [
                '#' + BTN_ID + ' {',
                '  position: fixed;',
                '  z-index: 99999;',
                '  width: 30px;',
                '  height: 30px;',
                '  border: 1px solid #e2e8f0;',
                '  border-radius: 6px;',
                '  background: #ffffff;',
                '  color: #475569;',
                '  font-size: 15px;',
                '  cursor: pointer;',
                '  display: flex;',
                '  align-items: center;',
                '  justify-content: center;',
                '  box-shadow: 0 1px 4px rgba(0,0,0,0.10);',
                '  transition: background 0.15s, color 0.15s, border-color 0.15s;',
                '  line-height: 1;',
                '}',
                '#' + BTN_ID + ':hover {',
                '  background: #eff6ff;',
                '  border-color: #93c5fd;',
                '  color: #2563eb;',
                '}',
                '#' + BTN_ID + '.maximizado {',
                '  top: 12px !important;',
                '  right: 12px !important;',
                '  background: #1e293b !important;',
                '  color: #f8fafc !important;',
                '  border-color: #475569 !important;',
                '}',
            ].join('\\n');
            doc.head.appendChild(s);
        }

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

        function posicionarBoton(iframe) {
            if (!iframe || maximizado) return;
            var rect = iframe.getBoundingClientRect();
            btn.style.top  = (rect.top  + 8) + 'px';
            btn.style.right = (win.innerWidth - rect.right + 8) + 'px';
        }

        function toggle() {
            var iframe = buscarIframe();
            if (!iframe) return;
            maximizado = !maximizado;

            if (maximizado) {
                estilosOriginales = {
                    position: iframe.style.position,
                    inset:    iframe.style.inset,
                    width:    iframe.style.width,
                    height:   iframe.style.height,
                    zIndex:   iframe.style.zIndex,
                };
                iframe.style.position = 'fixed';
                iframe.style.inset    = '0';
                iframe.style.width    = '100vw';
                iframe.style.height   = '100vh';
                iframe.style.zIndex   = '99998';

                var rail   = doc.getElementById('icon-rail');
                var topbar = doc.getElementById('top-bar');
                if (rail)   { estilosOriginales.railZI   = rail.style.zIndex;   rail.style.zIndex   = '1'; }
                if (topbar) { estilosOriginales.topbarZI = topbar.style.zIndex; topbar.style.zIndex = '1'; }

                btn.innerHTML = '&#x2715;';
                btn.title = 'Restaurar tabla';
                btn.classList.add('maximizado');

            } else {
                iframe.style.position = estilosOriginales.position || '';
                iframe.style.inset    = estilosOriginales.inset    || '';
                iframe.style.width    = estilosOriginales.width    || '';
                iframe.style.height   = estilosOriginales.height   || '';
                iframe.style.zIndex   = estilosOriginales.zIndex   || '';

                var rail   = doc.getElementById('icon-rail');
                var topbar = doc.getElementById('top-bar');
                if (rail)   rail.style.zIndex   = estilosOriginales.railZI   || '';
                if (topbar) topbar.style.zIndex  = estilosOriginales.topbarZI || '';

                btn.innerHTML = '&#x26F6;';
                btn.title = 'Maximizar tabla';
                btn.classList.remove('maximizado');

                // Reposicionar botón sobre el iframe restaurado
                win.setTimeout(function() {
                    posicionarBoton(iframe);
                }, 100);
            }
        }

        // ── Crear botón ────────────────────────────────────────────────
        var btn = doc.createElement('button');
        btn.id = BTN_ID;
        btn.innerHTML = '&#x26F6;';
        btn.title = 'Maximizar tabla';
        btn.onclick = toggle;

        // ── Buscar iframe y posicionar ──────────────────────────────────
        function check() {
            tries++;
            inyectarCSS();

            // Re-anclar botón si Streamlit lo desconectó
            if (doc.getElementById(BTN_ID) !== btn) {
                if (btn.parentNode) btn.parentNode.removeChild(btn);
                doc.body.appendChild(btn);
            }

            var iframe = buscarIframe();
            if (iframe) {
                posicionarBoton(iframe);
                return;
            }
            if (tries < MAX) {
                win.setTimeout(check, 500);
            }
        }
        win.setTimeout(check, 800);
    })();
    </script>
    """, height=0)
    </script>
    """, height=0)
