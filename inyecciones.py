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
    en un panel rojo fijo en pantalla. Así los errores quedan VISIBLES (también
    en capturas de pantalla), sin necesidad de abrir la consola del navegador.

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
        }).join('<br>──<br>');
        box.innerHTML = '<b>⚠️ Errores JS (' + win.__errLog.length + ')</b>'
          + '<span style="float:right;cursor:pointer;opacity:.7" '
          + 'onclick="this.parentNode.remove()">✕</span><br>' + items;
      }
      function log(m){ win.__errLog.push(String(m).slice(0,400)); render(); }
      win.addEventListener('error', function(ev){
        log('[error] ' + (ev.message || ev.error) + (ev.filename ? ' @ ' + ev.filename : ''));
      });
      win.addEventListener('unhandledrejection', function(ev){
        log('[promise] ' + ((ev.reason && ev.reason.message) || ev.reason));
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

      // ── CSS de paginación Opción A (Minimalista) ─────────────────────
      // Se inyecta dentro del iframe de AgGrid para garantizar que pisa
      // los estilos del tema. El custom_css del componente no siempre tiene
      // suficiente especificidad frente a los estilos del tema balham/material.
      var PAG_CSS = [
        /* Quitar fondo morado/rayado de la status bar */
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

        /* Franja de paginación limpia */
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

        /* Selector de tamaño a la izquierda */
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

        /* Resumen "1 a 50 de 5,000" */
        '.ag-paging-row-summary-panel { color: #64748b !important; font-size: 12px !important; }',
        '.ag-paging-row-summary-panel-number { color: #1e293b !important; font-weight: 600 !important; }',

        /* Descripción de página "Página X de Y" */
        '.ag-paging-description { color: #64748b !important; font-size: 12px !important; }',

        /* Botones de navegación — base */
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
        /* Ocultar el icono SVG interno que no carga en el iframe */
        '.ag-paging-button span, .ag-paging-button .ag-icon {',
        '  display: none !important;',
        '}',
        /* Reemplazar con caracteres Unicode visibles via ::after */
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

        /* ── Pestañas del panel lateral (Columnas/Filtros) ARRIBA y en  ── */
        /*    horizontal, en vez de verticales al costado.                  */
        /*    Se usa `order` para que los botones queden arriba sin         */
        /*    depender del orden del DOM (varía entre versiones de AgGrid). */
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
            inyectarCSS(d);   // <── inyección directa dentro del iframe
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
    Inspector de elementos v2 — tooltip enriquecido al pasar el cursor.

    Muestra: tipo de widget, label, key Python, valor actual, y para AgGrid:
    nombre de columna, valor de celda, fila, tipo de zona (header/cell/panel).

    Activación : ?inspector=1 en la URL  o  Alt+I
    Desactivación: quitar parámetro     o  Alt+I de nuevo

    Elementos reconocidos:
        • Widgets Streamlit  → tipo | label | key | valor actual
        • Botones / Popover  → tipo | texto visible
        • Tabs / Expander    → tipo | título
        • Métricas           → label | valor | delta
        • Plotly             → título | ejes X e Y
        • AgGrid celda       → columna | valor | fila nº
        • AgGrid header      → columna | tipo de ordenación activa
        • AgGrid panel cols  → columna listada | si está visible o no
        • AgGrid panel filtros → nombre del filtro
        • AgGrid paginación  → página actual / total
        • AgGrid status bar  → texto del panel de estado
        • Rail de navegación → nombre del reporte
    """
    components.html("""
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;

        if (win.__inspectorInit) return;
        win.__inspectorInit = true;

        // ── Activación ───────────────────────────────────────────────────
        function inspectorActivo() {
            return new URL(win.location.href).searchParams.get('inspector') === '1';
        }

        // ── Tooltip multilínea ───────────────────────────────────────────
        var tip = doc.createElement('div');
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

        // ── Badge ON/OFF ─────────────────────────────────────────────────
        var badge = doc.createElement('div');
        badge.id = 'el-inspector-badge';
        badge.style.cssText = [
            'position:fixed','bottom:10px','left:72px','z-index:2147483646',
            'background:#1e40af','color:#fff',
            'font:600 11px/1 -apple-system,sans-serif',
            'padding:5px 10px','border-radius:20px','display:none',
            'align-items:center','gap:6px','box-shadow:0 2px 8px rgba(0,0,0,0.3)'
        ].join(';');
        badge.innerHTML = '🔍 Inspector ON &nbsp;<span style="opacity:.6;font-weight:400">Alt+I para desactivar</span>';
        doc.body.appendChild(badge);

        function actualizarBadge() {
            badge.style.display = inspectorActivo() ? 'flex' : 'none';
        }
        actualizarBadge();

        // ── Helpers ──────────────────────────────────────────────────────
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
                var thumb = container.querySelector('[data-testid="stThumbValue"], ' +
                                                   '[aria-valuenow]');
                if (thumb) return thumb.getAttribute('aria-valuenow') || thumb.textContent.trim();
            }
            if (tipo === 'stDateInput') {
                var di = container.querySelector('input');
                return di ? di.value : '';
            }
            if (tipo === 'stCheckbox') {
                var cb = container.querySelector('input[type="checkbox"]');
                return cb ? (cb.checked ? 'marcado ✓' : 'desmarcado') : '';
            }
            return '';
        }

        // ── Intentar leer DOM interno del iframe de AgGrid ───────────────
        // (funciona mientras el iframe y el padre compartan origen o no haya
        //  bloqueo CORS estricto — en Streamlit local/cloud suele funcionar)
        function agGridInfo(mouseX, mouseY) {
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"], iframe[title*="aggrid"], iframe[title*="AgGrid"]');
            if (!frames.length) {
                // Buscar por posición si no hay atributo reconocible
                frames = doc.querySelectorAll('iframe');
            }
            for (var fi = 0; fi < frames.length; fi++) {
                var fr = frames[fi];
                var rect = fr.getBoundingClientRect();
                // ¿El cursor está dentro de este iframe?
                if (mouseX < rect.left || mouseX > rect.right ||
                    mouseY < rect.top  || mouseY > rect.bottom) continue;

                var fdoc = null;
                try { fdoc = fr.contentDocument; } catch(e) { continue; }
                if (!fdoc) continue;

                // Coordenadas relativas al iframe
                var rx = mouseX - rect.left;
                var ry = mouseY - rect.top;
                var inner = fdoc.elementFromPoint(rx, ry);
                if (!inner) continue;

                // ── Zona: celda de datos ──────────────────────────────────
                var cell = inner.closest('.ag-cell');
                if (cell) {
                    var colId   = cell.getAttribute('col-id') || '?';
                    var cellVal = cell.textContent.trim();
                    // Número de fila
                    var row = cell.closest('.ag-row');
                    var rowIdx = row ? (row.getAttribute('row-index') || '?') : '?';
                    // Tipo de fila (group, pinned-bottom = totales, normal)
                    var rowTipo = '';
                    if (row) {
                        if (row.classList.contains('ag-row-pinned')) rowTipo = ' [TOTAL]';
                        else if (row.classList.contains('ag-row-group')) rowTipo = ' [grupo]';
                    }
                    var lines = [
                        '📋 AgGrid › celda',
                        '  columna : ' + colId,
                        '  valor   : ' + (cellVal.length > 60 ? cellVal.slice(0,57)+'…' : cellVal),
                        '  fila nº : ' + rowIdx + rowTipo
                    ];
                    return lines.join('\n');
                }

                // ── Zona: header de columna ───────────────────────────────
                var hcell = inner.closest('.ag-header-cell');
                if (hcell) {
                    var hColId = hcell.getAttribute('col-id') || '?';
                    var hLabel = txt(hcell.querySelector('.ag-header-cell-text')) || hColId;
                    // Ordenación activa
                    var sortIcon = hcell.querySelector('.ag-sort-ascending-icon:not(.ag-hidden)');
                    var sortDesc = hcell.querySelector('.ag-sort-descending-icon:not(.ag-hidden)');
                    var sortInfo = sortIcon ? ' ↑ ascendente' : sortDesc ? ' ↓ descendente' : ' sin orden';
                    // ¿Tiene filtro activo?
                    var filtroActivo = hcell.querySelector('.ag-filter-active') ? ' 🔎 filtro activo' : '';
                    return [
                        '📋 AgGrid › encabezado',
                        '  col-id  : ' + hColId,
                        '  nombre  : ' + hLabel,
                        '  orden   :' + sortInfo + filtroActivo
                    ].join('\n');
                }

                // ── Zona: panel lateral — lista de columnas ───────────────
                var colItem = inner.closest('.ag-column-select-column');
                if (colItem) {
                    var colName = txt(colItem.querySelector('.ag-column-select-column-label')) || '?';
                    var visible = colItem.querySelector('input[type="checkbox"]');
                    var visStr  = visible ? (visible.checked ? 'visible ✓' : 'oculta') : '?';
                    return [
                        '📋 AgGrid › panel columnas',
                        '  columna : ' + colName,
                        '  estado  : ' + visStr
                    ].join('\n');
                }

                // ── Zona: panel lateral — filtros ─────────────────────────
                var filtItem = inner.closest('.ag-filter-toolpanel-instance');
                if (filtItem) {
                    var filtName = txt(filtItem.querySelector('.ag-filter-toolpanel-instance-header-text')) || '?';
                    return [
                        '📋 AgGrid › panel filtros',
                        '  filtro  : ' + filtName
                    ].join('\n');
                }

                // ── Zona: barra de paginación ─────────────────────────────
                var pag = inner.closest('.ag-paging-panel');
                if (pag) {
                    var pagTxt = pag.textContent.replace(/\s+/g, ' ').trim();
                    return [
                        '📋 AgGrid › paginación',
                        '  ' + pagTxt.slice(0, 80)
                    ].join('\n');
                }

                // ── Zona: status bar ──────────────────────────────────────
                var status = inner.closest('.ag-status-bar');
                if (status) {
                    return [
                        '📋 AgGrid › barra de estado',
                        '  ' + status.textContent.replace(/\s+/g, ' ').trim().slice(0, 80)
                    ].join('\n');
                }

                // ── Zona: botones del menú de columna (pin, sort, etc.) ───
                var menuItem = inner.closest('.ag-menu-option');
                if (menuItem) {
                    return '📋 AgGrid › menú: ' + txt(menuItem.querySelector('.ag-menu-option-text'));
                }

                // ── Fallback: dentro del iframe pero zona desconocida ─────
                if (fdoc.querySelector('.ag-root-wrapper')) {
                    return '📋 AgGrid › zona: ' + (inner.className || inner.tagName).toString().slice(0, 60);
                }
            }
            return null;
        }

        // ── Detección de elementos Streamlit ─────────────────────────────
        var WIDGET_MAP = {
            'stTextInput':    { ico: '✏️',  tipo: 'text_input'    },
            'stNumberInput':  { ico: '🔢',  tipo: 'number_input'  },
            'stTextArea':     { ico: '📝',  tipo: 'text_area'     },
            'stSelectbox':    { ico: '📌',  tipo: 'selectbox'     },
            'stMultiSelect':  { ico: '☑️',  tipo: 'multiselect'   },
            'stSlider':       { ico: '🎚️',  tipo: 'slider'        },
            'stSelectSlider': { ico: '🎚️',  tipo: 'select_slider' },
            'stDateInput':    { ico: '📅',  tipo: 'date_input'    },
            'stTimeInput':    { ico: '🕐',  tipo: 'time_input'    },
            'stCheckbox':     { ico: '✅',  tipo: 'checkbox'      },
        };

        function labelDe(el, mouseX, mouseY) {

            // 1. Widgets con label, key y valor
            for (var testid in WIDGET_MAP) {
                var container = el.closest('[data-testid="' + testid + '"]');
                if (!container) continue;
                var meta  = WIDGET_MAP[testid];
                var lbl   = labelWidget(container);
                var val   = valorWidget(container, testid);
                // Intentar extraer el key de Streamlit del atributo aria o del id del input
                var inp   = container.querySelector('input, select, textarea');
                var keyAt = inp ? (inp.getAttribute('aria-label') || inp.id || '') : '';
                // Filtrar keys internos de Streamlit (tienen formato "st-xx…")
                if (/^st-[a-z0-9]+$/i.test(keyAt)) keyAt = '';
                var lines = [meta.ico + ' ' + meta.tipo];
                if (lbl)   lines.push('  label : ' + lbl);
                if (keyAt) lines.push('  key   : ' + keyAt);
                if (val)   lines.push('  valor : ' + (val.length > 55 ? val.slice(0,52)+'…' : val));
                return lines.join('\n');
            }

            // 2. Botón de Streamlit (con data-testid en el key si existe)
            var btn = el.closest('[data-testid="baseButton-secondary"], [data-testid="baseButton-primary"], button[kind]');
            if (btn) {
                var btxt = btn.innerText.trim().replace(/\n/g, ' ');
                var bkey = btn.getAttribute('data-testid') || '';
                var blines = ['🔘 button'];
                if (btxt) blines.push('  texto : ' + btxt);
                if (bkey && bkey !== 'baseButton-secondary' && bkey !== 'baseButton-primary')
                    blines.push('  testid: ' + bkey);
                return blines.join('\n');
            }

            // 3. Popover
            var popover = el.closest('[data-testid="stPopover"]');
            if (popover) {
                var pbtn = popover.querySelector('button');
                var ptxt = pbtn ? pbtn.innerText.trim() : '?';
                var popen = popover.querySelector('[data-testid="stPopoverBody"]') ? ' (abierto)' : ' (cerrado)';
                return '🔽 popover\n  texto : ' + ptxt + '\n  estado: ' + popen.trim();
            }

            // 4. Tab activa / inactiva
            var tabBtn = el.closest('[data-baseweb="tab"]');
            if (tabBtn) {
                var isActive = tabBtn.getAttribute('aria-selected') === 'true';
                return '📑 tab\n  nombre: ' + tabBtn.innerText.trim() +
                       '\n  estado: ' + (isActive ? 'activa ✓' : 'inactiva');
            }

            // 5. Expander
            var expander = el.closest('[data-testid="stExpander"]');
            if (expander) {
                var etxt2 = expander.querySelector('summary p, summary span, .streamlit-expanderHeader p');
                var eopen = expander.querySelector('[data-testid="stExpanderDetails"]');
                var eIsOpen = eopen ? (eopen.style.display !== 'none' && eopen.style.visibility !== 'hidden') : false;
                return '📂 expander\n  título: ' + (etxt2 ? etxt2.textContent.trim() : '?') +
                       '\n  estado: ' + (eIsOpen ? 'abierto' : 'cerrado');
            }

            // 6. Métrica — label, valor y delta
            var metric = el.closest('[data-testid="stMetric"]');
            if (metric) {
                var mlbl2  = metric.querySelector('[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"]');
                var mval   = metric.querySelector('[data-testid="stMetricValue"]');
                var mdelta = metric.querySelector('[data-testid="stMetricDelta"]');
                var mlines = ['📊 metric'];
                if (mlbl2)  mlines.push('  label : ' + mlbl2.textContent.trim());
                if (mval)   mlines.push('  valor : ' + mval.textContent.trim());
                if (mdelta) mlines.push('  delta : ' + mdelta.textContent.trim());
                return mlines.join('\n');
            }

            // 7. Plotly — título + ejes
            var plotly = el.closest('.js-plotly-plot, [data-testid="stPlotlyChart"]');
            if (plotly) {
                var ptitle2 = plotly.querySelector('.gtitle, .g-gtitle');
                var xTitle  = plotly.querySelector('.g-xtitle');
                var yTitle  = plotly.querySelector('.g-ytitle');
                var plines  = ['📈 plotly'];
                plines.push('  título: ' + (ptitle2 ? ptitle2.textContent.trim() : '(sin título)'));
                if (xTitle) plines.push('  eje X : ' + xTitle.textContent.trim());
                if (yTitle) plines.push('  eje Y : ' + yTitle.textContent.trim());
                return plines.join('\n');
            }

            // 8. AgGrid — delegamos al lector de iframe
            var agEl = el.closest('[data-testid="stAgGrid"], .ag-root-wrapper');
            if (agEl || el.tagName === 'IFRAME') {
                var agInfo = agGridInfo(mouseX, mouseY);
                if (agInfo) return agInfo;
                return '📋 AgGrid tabla';
            }

            // 9. Rail de navegación
            var railIcon = el.closest('.rail-icon');
            if (railIcon) {
                var rname   = railIcon.getAttribute('data-tooltip') || railIcon.innerText.trim();
                var rActive = railIcon.classList.contains('active');
                return '🧭 nav\n  reporte: ' + rname + '\n  estado : ' + (rActive ? 'activo ✓' : 'inactivo');
            }

            // 10. Caption / aviso
            var caption = el.closest('[data-testid="stCaptionContainer"]');
            if (caption) {
                return 'ℹ️ caption\n  ' + caption.textContent.trim().slice(0, 80);
            }

            return null;
        }

        // ── Resaltado ────────────────────────────────────────────────────
        var elActual = null;
        function resaltarEl(el, etiqueta) {
            if (elActual) { elActual.style.outline = ''; elActual.style.outlineOffset = ''; }
            if (el && etiqueta) {
                el.style.outline = '2px solid #3b82f6';
                el.style.outlineOffset = '2px';
                elActual = el;
            } else { elActual = null; }
        }

        // ── Mousemove sobre el documento padre ───────────────────────────
        doc.addEventListener('mousemove', function(e) {
            if (!inspectorActivo()) {
                tip.style.opacity = '0';
                resaltarEl(null, null);
                return;
            }

            var el = e.target;
            var etiqueta = null;
            var cursor = el;

            // Intentar primero AgGrid (iframe) con las coordenadas del mouse
            var agInfo = agGridInfo(e.clientX, e.clientY);
            if (agInfo) {
                etiqueta = agInfo;
                // Resaltar el iframe como bloque
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
                // Recorrer DOM hasta encontrar widget (máx 12 niveles)
                for (var i = 0; i < 12 && cursor && cursor !== doc.body; i++) {
                    etiqueta = labelDe(cursor, e.clientX, e.clientY);
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
                // Calcular alto real del tooltip (multilínea)
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
        }, true);

        doc.addEventListener('mouseleave', function() {
            tip.style.opacity = '0';
            resaltarEl(null, null);
        });

        // ── Alt+I para activar/desactivar ────────────────────────────────
        doc.addEventListener('keydown', function(e) {
            if (e.altKey && (e.key === 'i' || e.key === 'I')) {
                var url = new URL(win.location.href);
                if (url.searchParams.get('inspector') === '1') {
                    url.searchParams.delete('inspector');
                } else {
                    url.searchParams.set('inspector', '1');
                }
                win.history.replaceState({}, '', url.toString());
                actualizarBadge();
                if (!inspectorActivo()) {
                    tip.style.opacity = '0';
                    resaltarEl(null, null);
                }
            }
        });

        var _push = win.history.pushState.bind(win.history);
        win.history.pushState = function() { _push.apply(win.history, arguments); actualizarBadge(); };
        win.addEventListener('popstate', actualizarBadge);

    })();
    </script>
    """, height=0, scrolling=False)
