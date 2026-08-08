"""inyecciones.diseno - modo de diseño visual (herramienta de desarrollo).

Deja fijar un elemento (mismo Fijar del inspector) y previsualizar cambios
de estilo en vivo sobre el DOM real — nunca persiste en estilos/ ni en
session_state. Activación: `?debug=1&diseno=1` juntos en la URL (releído en
cada tick, no una sola vez al cargar).

Acoplamiento con inspector.py (Regla viva, arquitectura.md #4 y #46): este
módulo LEE `win.__inspectorPinned` / `win.__inspectorUltimo`, que
`inyecciones/inspector.py` ya expone en `window.parent` para sobrevivir el
remount del iframe en cada rerun. Es una dependencia de solo lectura —
`inspector.py` no importa ni llama nada de este módulo, así que la regla
"ninguna función depende de otra" del paquete sigue valiendo en el sentido
de invocación directa; lo que se documenta acá es el contrato de datos
compartido (nombres de esas dos variables + la forma de `elemento.key`).
Si `inspector.py` alguna vez renombra esas variables o cambia qué guarda
`__inspectorUltimo`, este módulo se rompe — avisar en ambos lados.

El elemento pineado se re-resuelve por key en CADA ejecución del script
(nunca se confía en la referencia DOM capturada al momento del pin): un
rerun real preserva el nodo gracias a la reconciliación por key de
Streamlit, pero el propio iframe de este `components.html` se destruye y
recrea igual que el de `inspector.py`, así que los listeners/loops sí deben
reinstalarse cada vez (mismo patrón remove-old/add-new).
"""

import streamlit.components.v1 as components


def inject_diseno_visual():
    components.html("""
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;

        function disenoActivo() {
            var u = new URL(win.location.href);
            return u.searchParams.get('debug') === '1' && u.searchParams.get('diseno') === '1';
        }

        if (!win.__disenoState) {
            win.__disenoState = { porKey: {} };
        }

        function registroPara(key) {
            var st = win.__disenoState.porKey;
            if (!st[key]) {
                st[key] = {
                    key: key,
                    cssTextOriginal: null,
                    cambios: {},
                    transformState: { translateX: 0, translateY: 0, rotateDeg: 0 },
                    texto: { original: null, actual: null },
                    reorder: { tocado: false, ordenOriginal: null, ordenActual: null },
                    verOriginalActivo: false
                };
            }
            return st[key];
        }

        function elementoPineado() {
            // win.__inspectorUltimo.elemento es el nodo del momento del pin;
            // no confiar en esa referencia — re-resolver por key siempre.
            if (!win.__inspectorPinned || !win.__inspectorUltimo) return null;
            var key = win.__inspectorUltimo.key;
            if (!key) return null;
            var el = doc.querySelector('.st-key-' + key);
            return { key: key, el: el };  // el.el puede ser null (ya no renderiza)
        }

        var overlay = doc.getElementById('el-diseno-overlay');
        if (!overlay) {
            overlay = doc.createElement('div');
            overlay.id = 'el-diseno-overlay';
            overlay.style.cssText = [
                'position:fixed',
                'z-index:2147483600',
                'pointer-events:none',
                'border:2px solid #6c5ce7',
                'border-radius:4px',
                'box-sizing:border-box',
                'display:none'
            ].join(';');
            doc.body.appendChild(overlay);
        }

        var panel = doc.getElementById('el-diseno-panel');
        if (!panel) {
            panel = doc.createElement('div');
            panel.id = 'el-diseno-panel';
            panel.style.cssText = [
                'position:fixed',
                'top:0', 'right:0', 'bottom:0',
                'width:230px',
                'z-index:2147483600',
                'background:#101014',
                'color:#cfcfd6',
                'font:12px/1.6 "Courier New",monospace',
                'border-left:1px solid #6c5ce7',
                'padding:12px',
                'box-sizing:border-box',
                'overflow-y:auto',
                'white-space:pre-wrap',
                'display:none'
            ].join(';');
            doc.body.appendChild(panel);
        }

        function panelEspera() {
            overlay.style.display = 'none';
            panel.style.display = 'block';
            panel.textContent = 'Modo diseno activo\\n\\nClic derecho en un elemento para empezar (mismo Fijar del inspector).';
        }

        function panelPerdido(key) {
            overlay.style.display = 'none';
            panel.style.display = 'block';
            panel.textContent = 'Widget key: ' + key + '\\n\\n(el elemento pineado ya no existe en este render)';
        }

        function panelActivo(key) {
            panel.style.display = 'block';
            panel.textContent = 'Widget key: ' + key + '\\n\\n[Fase A: esqueleto -- controles en el proximo paso]';
        }

        function trackear(el) {
            var r = el.getBoundingClientRect();
            overlay.style.display = 'block';
            overlay.style.left = Math.round(r.left) + 'px';
            overlay.style.top = Math.round(r.top) + 'px';
            overlay.style.width = Math.round(r.width) + 'px';
            overlay.style.height = Math.round(r.height) + 'px';
        }

        // sync() es la UNICA fuente de verdad del tracking, y se llama tanto
        // desde el setInterval (cada 150ms, la garantia de fondo) como desde
        // scroll/resize (reaccion instantanea). NO depende de
        // requestAnimationFrame: probado en vivo que rAF puede no dispararse
        // nunca si la pestaña no esta componiendo frames (pestaña de fondo,
        // ventana minimizada) — dejar el tracking colgado de rAF solamente
        // deja la manija/outline congelada sin ningun error visible. rAF se
        // suma en la Fase A.2 SOLO como mejora de fluidez durante un arrastre
        // activo, nunca como el unico mecanismo de sync.
        function sync() {
            if (!disenoActivo()) {
                overlay.style.display = 'none';
                panel.style.display = 'none';
                return;
            }
            var res = elementoPineado();
            if (!res) {
                overlay.style.display = 'none';
                panelEspera();
                return;
            }
            if (!res.el) {
                panelPerdido(res.key);
                return;
            }
            registroPara(res.key);
            panelActivo(res.key);
            trackear(res.el);
        }

        // rerun-safety: el iframe de components.html se recrea en cada
        // rerun (igual que el de inspector.py) — limpiar el interval y los
        // listeners viejos antes de instalar los nuevos, o se acumulan para
        // siempre (ver mismo patron en inspector.py).
        if (win.__disenoPollInterval) { win.clearInterval(win.__disenoPollInterval); }
        if (win.__disenoScrollHandler) { win.removeEventListener('scroll', win.__disenoScrollHandler, true); }
        if (win.__disenoResizeHandler) { win.removeEventListener('resize', win.__disenoResizeHandler); }

        win.__disenoScrollHandler = sync;
        win.__disenoResizeHandler = sync;
        win.addEventListener('scroll', win.__disenoScrollHandler, true);
        win.addEventListener('resize', win.__disenoResizeHandler);

        win.__disenoPollInterval = win.setInterval(sync, 150);
        sync();

    })();
    </script>
    """, height=0, scrolling=False)
