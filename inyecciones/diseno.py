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

Fase A.2 agrega los controles de caja/geometría: manijas de resize/mover
sobre el overlay, y radio de borde / padding / borde completo / sombra /
"ver original" en el panel. Todo se aplica con
`elemento.style.setProperty(prop, valor, 'important')` y se trackea en
`win.__disenoState.porKey[key]` para poder reaplicarlo defensivamente en
cada ejecución del script (arquitectura.md #46: los estilos inline
sobreviven un rerun real, pero el iframe/listeners no).
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
                    bordeAncho: 0,
                    bordeColor: '#6c5ce7',
                    sombraNivel: 0,
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

        function elementoActivo() {
            // Helper para handlers de controles: re-resuelve SIEMPRE por key
            // en el momento del evento, nunca confia en una referencia
            // capturada cuando se construyeron los controles.
            var r = elementoPineado();
            return (r && r.el) ? { el: r.el, key: r.key, registro: registroPara(r.key) } : null;
        }

        function numDe(str, fallback) {
            var n = parseFloat(str);
            return isNaN(n) ? fallback : n;
        }

        // ---- overlay (outline + manijas) y panel lateral ----
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
                'font:12px/1.5 -apple-system,sans-serif',
                'border-left:1px solid #6c5ce7',
                'padding:12px',
                'box-sizing:border-box',
                'overflow-y:auto',
                'display:none'
            ].join(';');
            doc.body.appendChild(panel);
        }

        function panelEspera() {
            panel.dataset.builtForKey = '';
            panel.style.display = 'block';
            panel.style.whiteSpace = 'pre-wrap';
            panel.style.font = '12px/1.6 "Courier New",monospace';
            panel.textContent = 'Modo diseno activo\\n\\nClic derecho en un elemento para empezar (mismo Fijar del inspector).';
        }

        function panelPerdido(key) {
            panel.dataset.builtForKey = '';
            panel.style.display = 'block';
            panel.style.whiteSpace = 'pre-wrap';
            panel.style.font = '12px/1.6 "Courier New",monospace';
            panel.textContent = 'Widget key: ' + key + '\\n\\n(el elemento pineado ya no existe en este render)';
        }

        function trackear(el) {
            var r = el.getBoundingClientRect();
            overlay.style.display = 'block';
            overlay.style.left = Math.round(r.left) + 'px';
            overlay.style.top = Math.round(r.top) + 'px';
            overlay.style.width = Math.round(r.width) + 'px';
            overlay.style.height = Math.round(r.height) + 'px';
        }

        // ---- aplicar/retirar cambios sobre el elemento real ----
        function establecerCambio(elemento, registro, prop, valor) {
            if (valor === null) {
                delete registro.cambios[prop];
                elemento.style.removeProperty(prop);
            } else {
                registro.cambios[prop] = valor;
                elemento.style.setProperty(prop, valor, 'important');
            }
        }

        function aplicarTransform(elemento, registro) {
            var t = registro.transformState;
            if (t.translateX || t.translateY || t.rotateDeg) {
                elemento.style.setProperty('transform',
                    'translate(' + t.translateX + 'px,' + t.translateY + 'px) rotate(' + t.rotateDeg + 'deg)',
                    'important');
            } else {
                elemento.style.removeProperty('transform');
            }
        }

        function aplicarEstado(elemento, registro) {
            // snapshot para "ver original", una sola vez (primer touch de la key)
            if (registro.cssTextOriginal === null) {
                registro.cssTextOriginal = elemento.style.cssText || '';
            }
            if (registro.verOriginalActivo) {
                elemento.style.cssText = registro.cssTextOriginal;
                return;
            }
            // reaplicado defensivo completo — barato e idempotente, cubre el
            // caso de un nodo re-creado (no solo preservado) tras un rerun.
            for (var prop in registro.cambios) {
                elemento.style.setProperty(prop, registro.cambios[prop], 'important');
            }
            aplicarTransform(elemento, registro);
        }

        // ---- arrastre: resize (bordes/esquina) y mover (nudge) ----
        function iniciarArrastre(e, modo) {
            e.preventDefault();
            e.stopPropagation();
            var ctx = elementoActivo();
            if (!ctx) return;
            if (modo !== 'move') {
                // Tomar control manual del tamaño (arquitectura.md #47): un
                // width/height con !important NO alcanza en un item flex —
                // flex-basis (de 'flex: 1 1 0%', default de los stVerticalBlock/
                // stColumn de Streamlit) ignora height/width en el eje
                // principal, y max-width:100% (default de varios contenedores)
                // clampea el cruzado. Ninguna de las dos se gana agregando
                // !important a la MISMA propiedad — hay que neutralizar estas
                // tres antes de que width/height tengan efecto visual.
                establecerCambio(ctx.el, ctx.registro, 'flex', 'none');
                establecerCambio(ctx.el, ctx.registro, 'max-width', 'none');
                establecerCambio(ctx.el, ctx.registro, 'max-height', 'none');
            }
            var r = ctx.el.getBoundingClientRect();
            var startX = e.clientX, startY = e.clientY;
            var startW = r.width, startH = r.height;
            var startTX = ctx.registro.transformState.translateX;
            var startTY = ctx.registro.transformState.translateY;
            var cursorPrevio = doc.body.style.cursor;
            doc.body.style.userSelect = 'none';

            function onMove(ev) {
                var vivo = elementoActivo();
                if (!vivo) return;
                var dx = ev.clientX - startX, dy = ev.clientY - startY;
                if (modo === 'move') {
                    vivo.registro.transformState.translateX = Math.round(startTX + dx);
                    vivo.registro.transformState.translateY = Math.round(startTY + dy);
                    aplicarTransform(vivo.el, vivo.registro);
                } else {
                    if (modo.indexOf('e') !== -1) {
                        establecerCambio(vivo.el, vivo.registro, 'width',
                            Math.max(60, Math.round(startW + dx)) + 'px');
                    }
                    if (modo.indexOf('s') !== -1) {
                        establecerCambio(vivo.el, vivo.registro, 'height',
                            Math.max(40, Math.round(startH + dy)) + 'px');
                    }
                }
                trackear(vivo.el);
                actualizarReadouts(vivo.el, vivo.registro);
            }
            function onUp() {
                doc.body.style.userSelect = '';
                doc.body.style.cursor = cursorPrevio;
                doc.removeEventListener('mousemove', onMove);
                doc.removeEventListener('mouseup', onUp);
            }
            doc.addEventListener('mousemove', onMove);
            doc.addEventListener('mouseup', onUp);
        }

        function construirHandles() {
            if (doc.getElementById('el-diseno-rh-e')) return;  // idempotente

            function crearHandle(id, cssExtra, modo, cursor) {
                var h = doc.createElement('div');
                h.id = id;
                h.style.cssText = 'position:absolute;background:#6c5ce7;pointer-events:auto;cursor:' + cursor + ';' + cssExtra;
                h.addEventListener('mousedown', function(e) { iniciarArrastre(e, modo); });
                overlay.appendChild(h);
            }
            crearHandle('el-diseno-rh-e', 'top:50%;right:-5px;width:9px;height:34px;margin-top:-17px;border-radius:2px', 'e', 'ew-resize');
            crearHandle('el-diseno-rh-s', 'bottom:-5px;left:50%;width:34px;height:9px;margin-left:-17px;border-radius:2px', 's', 'ns-resize');
            crearHandle('el-diseno-rh-se', 'bottom:-6px;right:-6px;width:14px;height:14px;border-radius:3px', 'se', 'nwse-resize');

            var mover = doc.createElement('div');
            mover.id = 'el-diseno-mover';
            mover.title = 'Mover (nudge)';
            mover.style.cssText = 'position:absolute;top:-13px;left:-13px;width:24px;height:24px;border-radius:50%;background:#6c5ce7;pointer-events:auto;cursor:grab;display:flex;align-items:center;justify-content:center;color:#fff;font:600 13px sans-serif';
            mover.textContent = '+';
            mover.addEventListener('mousedown', function(e) { iniciarArrastre(e, 'move'); });
            overlay.appendChild(mover);
        }
        construirHandles();

        // ---- panel: controles interactivos ----
        function filaSoloLectura(etiquetaTexto, valorEl) {
            var div = doc.createElement('div');
            div.style.cssText = 'margin:6px 0;font-size:11px;color:#8b8b95;display:flex;justify-content:space-between;gap:8px';
            var lbl = doc.createElement('span');
            lbl.textContent = etiquetaTexto;
            div.appendChild(lbl);
            div.appendChild(valorEl);
            return div;
        }

        function spanValor(texto) {
            var s = doc.createElement('span');
            s.style.cssText = 'color:#e4e4e8;font-family:"Courier New",monospace';
            s.textContent = texto;
            return s;
        }

        function rango(min, max, step, valorInicial) {
            var inp = doc.createElement('input');
            inp.type = 'range';
            inp.min = min; inp.max = max; inp.step = step; inp.value = valorInicial;
            inp.style.cssText = 'width:100%;accent-color:#6c5ce7';
            return inp;
        }

        function filaControl(etiquetaTexto, controlEl, valorEl) {
            var div = doc.createElement('div');
            div.style.cssText = 'margin:12px 0';
            var lbl = doc.createElement('div');
            lbl.style.cssText = 'font-size:11px;color:#8b8b95;margin-bottom:4px;display:flex;justify-content:space-between';
            var txt = doc.createElement('span');
            txt.textContent = etiquetaTexto;
            lbl.appendChild(txt);
            lbl.appendChild(valorEl);
            div.appendChild(lbl);
            div.appendChild(controlEl);
            return div;
        }

        var SOMBRAS = ['', '0 1px 3px rgba(16,16,20,.14)', '0 4px 10px rgba(16,16,20,.18)',
                       '0 8px 20px rgba(16,16,20,.22)', '0 16px 34px rgba(16,16,20,.28)'];

        function construirControles(key, elemento, registro) {
            panel.innerHTML = '';
            panel.style.whiteSpace = 'normal';
            panel.style.font = '12px/1.5 -apple-system,sans-serif';

            var header = doc.createElement('div');
            header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #2a2a35';
            var headerKey = doc.createElement('div');
            headerKey.style.cssText = 'font-size:11px;color:#9385ec;word-break:break-all;font-family:"Courier New",monospace';
            headerKey.textContent = key;
            var btnSoltar = doc.createElement('button');
            btnSoltar.textContent = 'Soltar';
            btnSoltar.style.cssText = 'background:#2A2A35;color:#fff;border:0;border-radius:4px;padding:4px 8px;font:600 11px sans-serif;cursor:pointer;flex:0 0 auto';
            btnSoltar.addEventListener('click', function() {
                if (win.__inspectorTogglePin) win.__inspectorTogglePin(true);
            });
            header.appendChild(headerKey);
            header.appendChild(btnSoltar);
            panel.appendChild(header);

            var tamVal = spanValor('');
            panel.appendChild(filaSoloLectura('Tamaño', tamVal));
            var posVal = spanValor('');
            panel.appendChild(filaSoloLectura('Posición (nudge)', posVal));
            panel.__tamVal = tamVal;
            panel.__posVal = posVal;

            // radio de borde
            var radioVal = registro.cambios['border-radius']
                ? numDe(registro.cambios['border-radius'], 0)
                : numDe(win.getComputedStyle(elemento).borderTopLeftRadius, 0);
            var inpRadio = rango(0, 32, 1, radioVal);
            var radioLbl = spanValor(Math.round(radioVal) + 'px');
            inpRadio.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpRadio.value, 10);
                radioLbl.textContent = v + 'px';
                establecerCambio(ctx.el, ctx.registro, 'border-radius', v === 0 ? null : v + 'px');
            });
            panel.appendChild(filaControl('Radio de borde', inpRadio, radioLbl));

            // padding (uniforme)
            var padVal = registro.cambios['padding']
                ? numDe(registro.cambios['padding'], 0)
                : numDe(win.getComputedStyle(elemento).paddingTop, 0);
            var inpPad = rango(0, 48, 1, padVal);
            var padLbl = spanValor(Math.round(padVal) + 'px');
            inpPad.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpPad.value, 10);
                padLbl.textContent = v + 'px';
                establecerCambio(ctx.el, ctx.registro, 'padding', v === 0 ? null : v + 'px');
            });
            panel.appendChild(filaControl('Padding', inpPad, padLbl));

            // borde completo (ancho + color -> shorthand 'border')
            var inpBordeAncho = rango(0, 8, 1, registro.bordeAncho);
            var bordeLbl = spanValor(registro.bordeAncho + 'px');
            var inpBordeColor = doc.createElement('input');
            inpBordeColor.type = 'color';
            inpBordeColor.value = registro.bordeColor;
            inpBordeColor.style.cssText = 'width:100%;height:24px;border:0;border-radius:4px;padding:0;cursor:pointer;margin-top:8px;background:transparent';
            function aplicarBorde(ctx) {
                establecerCambio(ctx.el, ctx.registro, 'border',
                    ctx.registro.bordeAncho === 0 ? null : (ctx.registro.bordeAncho + 'px solid ' + ctx.registro.bordeColor));
            }
            inpBordeAncho.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.bordeAncho = parseInt(inpBordeAncho.value, 10);
                bordeLbl.textContent = ctx.registro.bordeAncho + 'px';
                aplicarBorde(ctx);
            });
            inpBordeColor.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.bordeColor = inpBordeColor.value;
                aplicarBorde(ctx);
            });
            var bordeWrap = doc.createElement('div');
            bordeWrap.appendChild(inpBordeAncho);
            bordeWrap.appendChild(inpBordeColor);
            panel.appendChild(filaControl('Borde completo', bordeWrap, bordeLbl));

            // sombra
            var inpSombra = rango(0, 4, 1, registro.sombraNivel);
            var sombraLbl = spanValor(registro.sombraNivel === 0 ? 'sin sombra' : ('nivel ' + registro.sombraNivel));
            inpSombra.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.sombraNivel = parseInt(inpSombra.value, 10);
                sombraLbl.textContent = ctx.registro.sombraNivel === 0 ? 'sin sombra' : ('nivel ' + ctx.registro.sombraNivel);
                establecerCambio(ctx.el, ctx.registro, 'box-shadow',
                    ctx.registro.sombraNivel === 0 ? null : SOMBRAS[ctx.registro.sombraNivel]);
            });
            panel.appendChild(filaControl('Sombra', inpSombra, sombraLbl));

            // ver original
            var btnOriginal = doc.createElement('button');
            btnOriginal.textContent = registro.verOriginalActivo ? 'Ver con cambios' : 'Ver original';
            btnOriginal.style.cssText = 'width:100%;margin-top:14px;background:#3C3489;color:#fff;border:0;border-radius:4px;padding:7px;font:600 11px sans-serif;cursor:pointer';
            btnOriginal.addEventListener('click', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.verOriginalActivo = !ctx.registro.verOriginalActivo;
                btnOriginal.textContent = ctx.registro.verOriginalActivo ? 'Ver con cambios' : 'Ver original';
                aplicarEstado(ctx.el, ctx.registro);
            });
            panel.appendChild(btnOriginal);
        }

        function actualizarReadouts(elemento, registro) {
            if (!panel.__tamVal) return;
            var r = elemento.getBoundingClientRect();
            panel.__tamVal.textContent = Math.round(r.width) + ' x ' + Math.round(r.height) + ' px';
            panel.__posVal.textContent = Math.round(registro.transformState.translateX) + ', ' + Math.round(registro.transformState.translateY) + ' px';
        }

        // sync() es la UNICA fuente de verdad del tracking, y se llama tanto
        // desde el setInterval (cada 150ms, la garantia de fondo) como desde
        // scroll/resize (reaccion instantanea). NO depende de
        // requestAnimationFrame: probado en vivo que rAF puede no dispararse
        // nunca si la pestaña no esta componiendo frames (pestaña de fondo,
        // ventana minimizada) — dejar el tracking colgado de rAF solamente
        // deja la manija/outline congelada sin ningun error visible. El
        // arrastre (resize/mover) tampoco usa rAF: aplica los cambios
        // directo en cada 'mousemove', que ya alcanza para verse fluido.
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
                overlay.style.display = 'none';
                panelPerdido(res.key);
                return;
            }
            var registro = registroPara(res.key);
            aplicarEstado(res.el, registro);
            trackear(res.el);
            if (panel.dataset.builtForKey !== res.key) {
                construirControles(res.key, res.el, registro);
                panel.dataset.builtForKey = res.key;
            }
            panel.style.display = 'block';
            actualizarReadouts(res.el, registro);
        }

        // rerun-safety: el iframe de components.html se recrea en cada
        // rerun (igual que el de inspector.py) — limpiar el interval y los
        // listeners viejos antes de instalar los nuevos, o se acumulan para
        // siempre (ver mismo patron en inspector.py). Las manijas y los
        // controles del panel NO necesitan este tratamiento: se crean una
        // sola vez de forma idempotente y sus handlers re-resuelven el
        // elemento activo en cada evento (elementoActivo()), nunca dependen
        // de una referencia capturada al construirlos.
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
