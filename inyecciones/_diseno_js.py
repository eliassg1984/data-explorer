"""inyecciones._diseno_js - el JS del modo de diseno visual.

Blob de 794 lineas que estaba embebido como un unico components.html
DENTRO de inject_diseno_visual. Se saco el 2026-08-08, mismo tratamiento
que _inspector_js.py.

Lleva el placeholder `__PALETA__`, que el llamador sustituye por el JSON
de _PALETA. No es un f-string a proposito: el JS esta lleno de llaves.

NO CONVERTIR A RAW STRING, y si se toca, verificar parsed-vs-parsed (no
comparando texto fuente). El porque, con el bug real que costo, esta en
arquitectura.md regla #56.

Ver el docstring de diseno.py para que hace el modo diseno, como se
activa (?debug=1&diseno=1) y su acoplamiento de solo-lectura con el pin
de inspector.py.
"""

JS = """
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;
        var PALETA = __PALETA__;

        function disenoActivo() {
            var u = new URL(win.location.href);
            return u.searchParams.get('debug') === '1' && u.searchParams.get('diseno') === '1';
        }

        if (!win.__disenoState) {
            win.__disenoState = { porKey: {}, panelColapsado: false };
        }
        if (win.__disenoState.panelColapsado === undefined) {
            win.__disenoState.panelColapsado = false;
        }
        if (!win.__disenoState.mocks) { win.__disenoState.mocks = []; }
        if (win.__disenoState.mockN === undefined) { win.__disenoState.mockN = 0; }
        if (!win.__disenoState.mockPos) { win.__disenoState.mockPos = 'despues'; }
        // Sub-pin (regla #157): {key, clase} del hijo SIN key propia al que
        // bajo el pin, o null. Se guarda la CLASE, nunca el nodo — un rerun
        // lo recrea, igual que al widget con key.
        if (win.__disenoState.sub === undefined) { win.__disenoState.sub = null; }

        // El indice es el `id` de elementoPineado(), no la key: con sub-pin
        // vale `compras_prov_card_ranking .cp-rank-tit`, asi la tarjeta y
        // cada hijo pineable llevan su propio juego de cambios.
        function registroPara(id) {
            var st = win.__disenoState.porKey;
            if (!st[id]) {
                st[id] = {
                    key: id,
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
            return st[id];
        }

        // ── Sub-pin: bajar a un hijo sin key propia (regla #157) ─────────
        // El pin del inspector se ancla SIEMPRE al contenedor con
        // `st-key-*` mas cercano. Un titulo de `st.markdown`
        // (`<div class="cp-rank-tit">`) no tiene key, asi que pinearlo
        // pineaba la TARJETA entera: "Mover" corria los 929x388 px del
        // contenedor y el titulo no se movia ni un pixel DENTRO de el.
        //
        // Clases "de autor" = las que escribe ESTE proyecto en su HTML. Las
        // de Streamlit no sirven como selector estable: `st-emotion-cache-
        // 1f3w014` cambia con cada build y `stMarkdown`/`stVerticalBlock`
        // matchean media pagina. `ag-*` queda afuera aparte: el estilo de
        // AgGrid va por su `custom_css`, no por `estilos/`.
        var CLASES_DE_STREAMLIT = { 'element-container': 1, 'row-widget': 1,
                                    'main': 1, 'block-container': 1, 'stApp': 1 };
        function esClaseDeAutor(c) {
            if (!c || CLASES_DE_STREAMLIT[c]) return false;
            if (c.indexOf('st-') === 0) return false;   // st-key-*, st-emotion-cache-*, st-ae
            if (c.indexOf('ag-') === 0) return false;   // internos de AgGrid
            if (c.indexOf('css-') === 0) return false;  // emotion, clase de estilo
            // Gemela de la anterior y MENOS obvia: @emotion/babel-plugin le
            // pone a cada componente una clase "target" sin prefijo alguno
            // (`e1rw0b1u1`, `eqmt79k2`, `etxdrby0`). Verificado en vivo: sin
            // este corte se colaban 3 de esas ANTES de `.cp-rank-tit` en el
            // arbol. Cambian con cada build de Streamlit, o sea que como
            // selector para pegar en estilos/ son una trampa.
            if (c.indexOf('-') === -1 && c.length >= 6 && /^e[a-z0-9]*[0-9]/.test(c)) return false;
            return !/^st[A-Z]/.test(c);                 // stMarkdown, stVerticalBlock, ...
        }

        // Hijos del widget pineado que tienen clase propia pero NO key: los
        // unicos que el modo diseno no podia tocar. Se excluye lo que viva
        // dentro de OTRO `st-key-` mas adentro (eso es otro widget: se pinea
        // por su key, no bajando desde aca) y lo que sea SVG (un Plotly sin
        // key propia inunda la lista con `main-svg`/`trace`/`point`).
        function hijosConClasePropia(key) {
            var base = doc.querySelector('.st-key-' + key);
            if (!base) return [];
            var out = [], vistas = {};
            var cand = base.querySelectorAll('[class]');
            for (var i = 0; i < cand.length && out.length < 12; i++) {
                var n = cand[i];
                if (n.ownerSVGElement || (n.tagName || '').toLowerCase() === 'svg') continue;
                var cur = n.parentElement, propio = true;
                while (cur && cur !== base) {
                    if (/st-key-[A-Za-z0-9_]+/.test((cur.className || '').toString())) { propio = false; break; }
                    cur = cur.parentElement;
                }
                if (!propio || cur !== base) continue;
                var cls = n.classList || [];
                for (var j = 0; j < cls.length; j++) {
                    if (!esClaseDeAutor(cls[j]) || vistas[cls[j]]) continue;
                    vistas[cls[j]] = 1;
                    out.push(cls[j]);
                }
            }
            return out;
        }

        function elementoPineado() {
            // win.__inspectorUltimo.elemento es el nodo del momento del pin;
            // no confiar en esa referencia — re-resolver por key siempre.
            if (!win.__inspectorPinned || !win.__inspectorUltimo) return null;
            var key = win.__inspectorUltimo.key;
            if (!key) return null;
            var base = doc.querySelector('.st-key-' + key);
            var sub = win.__disenoState.sub;
            // El sub muere con su key: si el pin salto a otro widget, lo que
            // haya guardado ya no aplica (y su clase podria existir alla
            // adentro y pinear un hijo distinto sin aviso).
            if (sub && sub.key !== key) { win.__disenoState.sub = null; sub = null; }
            if (!sub) return { key: key, sub: '', id: key, el: base };
            // `el: null` si el hijo no esta => panelPerdido, igual que con la
            // key. Caer de vuelta al contenedor seria peor: aplicaria los
            // cambios del hijo a la tarjeta entera sin que nadie lo pida.
            return { key: key, sub: sub.clase, id: key + ' .' + sub.clase,
                     el: base ? base.querySelector('.' + sub.clase) : null };
        }

        function elementoActivo() {
            // Helper para handlers de controles: re-resuelve SIEMPRE por key
            // en el momento del evento, nunca confia en una referencia
            // capturada cuando se construyeron los controles.
            var r = elementoPineado();
            return (r && r.el) ? { el: r.el, key: r.key, sub: r.sub, id: r.id,
                                   registro: registroPara(r.id) } : null;
        }

        function bajarASub(clase) {
            var r = elementoPineado();
            if (!r) return;
            win.__disenoState.sub = { key: r.key, clase: clase };
            panel.dataset.builtForKey = '';   // fuerza reconstruir con el sub
            sync();
        }

        // ── Jerarquía (regla #155) ───────────────────────────────────────
        // Duplica A PROPOSITO cadenaKeys()/keyDeElemento() de
        // _inspector_js.py (mismo criterio que copiarTextoDiseno() con
        // copiarTexto(): son dos realms/iframes separados y "ninguna
        // funcion depende de otra" es la regla del paquete inyecciones/ —
        // ver docstring de diseno.py). El modo diseno no tiene su PROPIO
        // pin: lee win.__inspectorPinned/__inspectorUltimo (acoplamiento de
        // solo lectura documentado ahi), asi que saltar de key tambien pasa
        // por las funciones que el inspector expuso en win, igual que ya
        // hace el boton "Soltar" de mas abajo con __inspectorTogglePin.
        function cadenaKeysDiseno(el) {
            var out = [];
            var cur = el;
            while (cur && cur !== doc.body && out.length < 12) {
                var m = /st-key-([A-Za-z0-9_]+)/.exec((cur.className || '').toString());
                if (m && out.indexOf(m[1]) === -1) out.push(m[1]);
                cur = cur.parentElement;
            }
            return out;
        }

        function saltarADiseno(key) {
            var el = doc.querySelector('.st-key-' + key);
            if (!el || !win.__inspectorMouseMoveHandler) return;
            // Saltar de contenedor suelta el sub-pin. Tambien es el camino de
            // VUELTA: con un sub activo la fila de su propia key deja de ser
            // "la actual" y vuelve a ser clicable, y este clic sube el pin.
            win.__disenoState.sub = null;
            var r = el.getBoundingClientRect();
            var cx = r.left + Math.min(12, r.width / 2);
            var cy = r.top + Math.min(12, r.height / 2);
            if (win.__inspectorPinned && win.__inspectorTogglePin) win.__inspectorTogglePin(true);
            win.__inspectorMouseMoveHandler({ target: el, clientX: cx, clientY: cy });
            if (win.__inspectorTogglePin) win.__inspectorTogglePin();
            panel.dataset.builtForKey = '';   // fuerza reconstruir con la key nueva
            sync();
        }

        function numDe(str, fallback) {
            var n = parseFloat(str);
            return isNaN(n) ? fallback : n;
        }

        // ---- mocks: elementos de mentira para ver "como se veria" -------
        // Nacen con la clase `st-key-<key>` A PROPOSITO. elementoPineado()
        // resuelve por `.st-key-<key>` y el inspector saca la key del
        // className con el mismo regex, asi que un mock se fija con clic
        // derecho igual que un widget real y hereda TODO el panel
        // (tipografia, color, borde, sombra, mover, resize) sin una linea
        // de codigo extra. No tocan Python ni estilos/: son DOM efimero y
        // mueren al recargar la pagina, como el resto del modo diseno.
        function colorPaleta(nombre) {
            for (var i = 0; i < PALETA.length; i++) {
                if (PALETA[i].nombre === nombre) return PALETA[i].hex;
            }
            return PALETA.length ? PALETA[0].hex : 'currentColor';
        }

        var TIPOS_MOCK = [['texto', 'Texto'], ['linea', 'Línea'],
                          ['barra', 'Barra'], ['espacio', 'Espacio']];

        function nodoMock(m) {
            var el = doc.createElement('div');
            el.className = 'st-key-' + m.key;
            el.setAttribute('data-diseno-mock', m.tipo);
            if (m.tipo === 'texto') {
                el.textContent = m.texto;
                el.contentEditable = 'true';
                el.spellcheck = false;
                // Se escribe en el lugar. El atajo "C" del inspector ya
                // ignora isContentEditable, asi que tipear una c aca no
                // dispara "copiar para IA" (ver _inspector_js.py).
                el.style.cssText = 'font:600 14px/1.4 -apple-system,"Segoe UI",sans-serif;padding:4px 2px;outline:0;cursor:text;color:'
                    + colorPaleta('Texto principal');
                el.addEventListener('input', function() { m.texto = el.textContent; });
            } else if (m.tipo === 'linea') {
                el.style.cssText = 'height:1px;margin:8px 0;opacity:.35;background:' + colorPaleta('Gris texto');
            } else if (m.tipo === 'barra') {
                el.style.cssText = 'height:34px;margin:6px 0;border-radius:8px;background:' + colorPaleta('Acento');
            } else {
                // Aire: no pinta nada, pero hay que PODER verlo y agarrarlo
                // mientras se disena -> outline, que no ocupa layout (un
                // border si, y falsearia el alto que se esta probando).
                el.style.cssText = 'height:16px;opacity:.5;outline-offset:-1px;outline:1px dashed ' + colorPaleta('Gris texto');
            }
            return el;
        }

        function anclaEfectiva(m) {
            var ancla = doc.querySelector('.st-key-' + m.anclaKey);
            // Con sub-pin el ancla es el HIJO, no la tarjeta: insertar "antes"
            // de un titulo y "antes" de la tarjeta que lo contiene son dos
            // lugares distintos, y el pin ya dice cual de los dos se eligio.
            if (ancla && m.anclaSub) ancla = ancla.querySelector('.' + m.anclaSub);
            if (!ancla || !ancla.parentNode) return null;
            // 'despues' se encadena detras del ULTIMO hermano ya insertado:
            // sin esto, agregar titulo y despues linea los deja al reves
            // (cada uno entra pegado al ancla y empuja al anterior).
            // 'antes' y 'dentro' salen en orden solos.
            if (m.posicion !== 'despues') return ancla;
            var ms = win.__disenoState.mocks;
            for (var i = 0; i < ms.length && ms[i].key !== m.key; i++) {
                if (ms[i].anclaKey !== m.anclaKey || ms[i].posicion !== 'despues') continue;
                if ((ms[i].anclaSub || '') !== (m.anclaSub || '')) continue;
                var prev = doc.querySelector('.st-key-' + ms[i].key);
                if (prev && prev.parentNode === ancla.parentNode) ancla = prev;
            }
            return ancla;
        }

        function insertarMock(m) {
            var ancla = anclaEfectiva(m);
            if (!ancla) return false;
            var el = nodoMock(m);
            if (m.posicion === 'antes') ancla.parentNode.insertBefore(el, ancla);
            else if (m.posicion === 'dentro') ancla.appendChild(el);
            else ancla.parentNode.insertBefore(el, ancla.nextSibling);
            // El nodo es NUEVO (llegamos aca porque un rerun se llevo el
            // anterior): reaplicarle lo que el panel ya le habia editado,
            // igual que aplicarEstado hace con los widgets reales.
            var reg = win.__disenoState.porKey[m.key];
            if (reg) {
                Object.keys(reg.cambios).forEach(function(prop) {
                    el.style.setProperty(prop, reg.cambios[prop], 'important');
                });
                aplicarTransform(el, reg);
            }
            return true;
        }

        function reponerMocks() {
            var ms = win.__disenoState.mocks;
            for (var i = 0; i < ms.length; i++) {
                if (!doc.querySelector('.st-key-' + ms[i].key)) insertarMock(ms[i]);
            }
        }

        function agregarMock(tipo) {
            var res = elementoPineado();
            if (!res || !res.el) return;   // sin ancla no hay donde insertar
            win.__disenoState.mockN += 1;
            var m = {
                key: 'diseno_' + tipo + '_' + win.__disenoState.mockN,
                tipo: tipo,
                anclaKey: res.key,
                anclaSub: res.sub,
                posicion: win.__disenoState.mockPos,
                texto: 'Texto de prueba'
            };
            win.__disenoState.mocks.push(m);
            insertarMock(m);
            panel.dataset.builtForKey = '';   // cambio el contador de la lista
            sync();
        }

        function quitarMock(key) {
            var n = doc.querySelector('.st-key-' + key);
            if (n && n.parentNode) n.parentNode.removeChild(n);
            win.__disenoState.mocks = win.__disenoState.mocks.filter(function(m) {
                return m.key !== key;
            });
            delete win.__disenoState.porKey[key];
        }

        function esMock(key) {
            return win.__disenoState.mocks.some(function(m) { return m.key === key; });
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

        var PANEL_CSS_EXPANDIDO = [
            'position:fixed',
            'top:0', 'right:0', 'bottom:0',
            'width:230px',
            'z-index:2147483600',
            'background:#101014',
            'color:#cfcfd6',
            'font:12px/1.5 -apple-system,sans-serif',
            'border-left:1px solid #6c5ce7',
            // padding-bottom aparte y mas grande: Streamlit Cloud clava su
            // propio badge "Manage app" fixed al fondo del viewport, ancho
            // completo, por ENCIMA de este panel (z-index mayor, fuera de
            // nuestro control). Sin este colchon, las ultimas filas quedan
            // tapadas aun con scroll al fondo — no es que falte scrollear,
            // es que ese espacio ya no es clickeable.
            'padding:12px 12px 64px 12px',
            'box-sizing:border-box',
            'overflow-y:auto',
            'display:none'
        ].join(';');

        var panel = doc.getElementById('el-diseno-panel');
        if (!panel) {
            panel = doc.createElement('div');
            panel.id = 'el-diseno-panel';
            panel.style.cssText = PANEL_CSS_EXPANDIDO;
            doc.body.appendChild(panel);
        }

        function botonColapsar() {
            var b = doc.createElement('button');
            b.textContent = '–';
            b.title = 'Ocultar panel (Alt+D)';
            b.style.cssText = 'background:#2A2A35;color:#fff;border:0;border-radius:4px;width:22px;height:22px;font:600 14px/1 sans-serif;cursor:pointer;flex:0 0 auto';
            b.addEventListener('click', function(ev) {
                ev.stopPropagation();
                win.__disenoState.panelColapsado = true;
                panel.dataset.builtForKey = '';
                sync();
            });
            return b;
        }

        function pintarPill() {
            var res = elementoPineado();
            var etiqueta = (res && res.el) ? ('🎨 ' + res.id) : '🎨 Modo diseno';
            panel.style.cssText = [
                'position:fixed','bottom:16px','right:16px','z-index:2147483600',
                'background:#101014','color:#cfcfd6','border:1px solid #6c5ce7',
                'border-radius:20px','padding:7px 14px',
                'font:600 12px/1.3 -apple-system,sans-serif',
                'cursor:pointer','box-shadow:0 2px 8px rgba(0,0,0,.35)',
                'display:block','white-space:nowrap'
            ].join(';');
            panel.textContent = etiqueta + '  ·  expandir (Alt+D)';
            panel.__tamVal = null;
            panel.__posVal = null;
            panel.onclick = function() {
                win.__disenoState.panelColapsado = false;
                panel.dataset.builtForKey = '';
                sync();
            };
        }

        function panelEspera() {
            panel.dataset.builtForKey = '';
            panel.style.cssText = PANEL_CSS_EXPANDIDO;
            panel.style.display = 'block';
            panel.onclick = null;
            panel.innerHTML = '';
            var header = doc.createElement('div');
            header.style.cssText = 'display:flex;justify-content:flex-end;margin-bottom:8px';
            header.appendChild(botonColapsar());
            panel.appendChild(header);
            var texto = doc.createElement('div');
            texto.style.cssText = 'font:12px/1.6 "Courier New",monospace;white-space:pre-wrap';
            texto.textContent = 'Modo diseno activo\\n\\nClic derecho en un elemento para empezar (mismo Fijar del inspector). Insertar texto/linea/barra sale del mismo lugar: el elemento fijado es el ancla.';
            panel.appendChild(texto);
        }

        function panelPerdido(key) {
            panel.dataset.builtForKey = '';
            panel.style.cssText = PANEL_CSS_EXPANDIDO;
            panel.style.display = 'block';
            panel.onclick = null;
            panel.innerHTML = '';
            var header = doc.createElement('div');
            header.style.cssText = 'display:flex;justify-content:flex-end;margin-bottom:8px';
            header.appendChild(botonColapsar());
            panel.appendChild(header);
            var texto = doc.createElement('div');
            texto.style.cssText = 'font:12px/1.6 "Courier New",monospace;white-space:pre-wrap';
            texto.textContent = 'Widget key: ' + key + '\\n\\n(el elemento pineado ya no existe en este render)';
            panel.appendChild(texto);
        }

        // El contorno se dibuja SEPARADO del elemento, no encima. Iba en su
        // rect exacto y con box-sizing:border-box, o sea que sus 2px violetas
        // caian justo sobre el borde propio del elemento: al mover "Borde
        // completo" no se veia nada y habia que soltar el pin para juzgar el
        // cambio (reportado 2026-08-22, ver regla #166).
        // No rompe el redimensionado: iniciarArrastre() mide
        // ctx.el.getBoundingClientRect(), nunca el overlay. Y las manijas,
        // que son hijas suyas, quedan 4px mas afuera — de paso dejan de
        // taparle las esquinas.
        var SEPARACION_CONTORNO = 4;

        function trackear(el) {
            var r = el.getBoundingClientRect();
            var s = SEPARACION_CONTORNO;
            overlay.style.display = win.__disenoContornoOculto ? 'none' : 'block';
            overlay.style.left = Math.round(r.left - s) + 'px';
            overlay.style.top = Math.round(r.top - s) + 'px';
            overlay.style.width = Math.round(r.width + s * 2) + 'px';
            overlay.style.height = Math.round(r.height + s * 2) + 'px';
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

        // Widgets tipo boton (st.pills/segmented_control, o un st.button/
        // st.popover suelto): el key vive en un WRAPPER de layout, y lo
        // visualmente relevante (borde, relleno, tipografia, color) esta en
        // el/los <button> de adentro, que no tienen key propia. Pinear
        // "Apilado" pinea el grupo entero; pinear un popover pinea su
        // wrapper invisible. Sin esto, "Radio de borde"/"Padding"/etc.
        // tocan una caja sin efecto visual (o agregan espacio vacio
        // alrededor de un boton que se ve igual de chico).
        //
        // El criterio para redirigir es de AREA, no de "hay un boton
        // adentro": una tarjeta grande (chartcard_cascada) tiene botones
        // de expandir ▸ salpicados por todas las filas — redirigir ahi
        // sería una sorpresa (tocar "color de fondo" de la tarjeta
        // terminaría pintando flechitas). Solo redirige cuando el/los
        // botones ocupan la MAYOR PARTE del propio elemento en ancho o
        // alto (>=60%), es decir, cuando el elemento pineado ES basicamente
        // el boton, no un contenedor mas grande que de casualidad tiene
        // botones en algun lado.
        function destinosDeEstilo(elemento) {
            var enGrupo = elemento.querySelectorAll('[data-testid="stButtonGroup"] button');
            var candidatos = enGrupo.length ? Array.prototype.slice.call(enGrupo)
                                             : Array.prototype.slice.call(elemento.querySelectorAll('button'));
            // Filtrar candidatos de 0x0 ANTES de contar: un st.button con
            // help= (tooltip) renderiza un SEGUNDO <button> fantasma de
            // 0x0px (mismo testid, mismo texto) — encontrado en
            // navbtn_Compras, que tiene help=grupo. Sin este filtro, "1
            // boton real + 1 fantasma" contaba como 2 y el guard de
            // cantidad de abajo (pensado para el rail) lo trataba igual
            // que 12 botones apilados: dejaba de redirigir y el font-size
            // se aplicaba al wrapper en vez de al boton visible — "el
            // control no hace nada" otra vez, mismo sintoma que la regla
            // #48, causa nueva.
            candidatos = candidatos.filter(function(b) {
                var rb = b.getBoundingClientRect();
                return rb.width > 0 && rb.height > 0;
            });
            if (!candidatos.length) return [elemento];
            // Varios botones SUELTOS (fuera de un stButtonGroup) = el
            // elemento es una LISTA de botones, no un boton. El caso real
            // es el rail (compras_tabs_row): 12 st.button apilados con
            // use_container_width, cada uno casi tan ancho como la tarjeta.
            // La SUMA de anchos de una COLUMNA da ~10x el ancho del
            // contenedor, asi que el >=60% de abajo siempre daba verdadero
            // y los controles de estilo terminaban en los items del rail
            // mientras el contorno violeta seguia marcando la tarjeta.
            if (!enGrupo.length && candidatos.length > 1) return [elemento];
            var rEl = elemento.getBoundingClientRect();
            if (rEl.width <= 0 || rEl.height <= 0) return [elemento];
            // Ancho: SUMA — llegado aca son pills de un MISMO stButtonGroup
            // (se reparten la fila entre todos) o un unico boton suelto.
            // Alto: MAXIMO (comparten la fila, no se apilan).
            var anchoBotones = 0, altoMaxBotones = 0;
            candidatos.forEach(function(b) {
                var rb = b.getBoundingClientRect();
                anchoBotones += rb.width;
                altoMaxBotones = Math.max(altoMaxBotones, rb.height);
            });
            var ratioAncho = anchoBotones / rEl.width;
            var ratioAlto = altoMaxBotones / rEl.height;
            if (Math.max(ratioAncho, ratioAlto) < 0.6) return [elemento];
            return candidatos;
        }

        // Props de GEOMETRIA: siempre sobre `elemento` (asi coincide con el
        // overlay/las manijas, que trackean su bounding box). Todo lo
        // demas en `cambios` es "estilo" y va a destinosDeEstilo().
        var PROPS_GEOMETRIA = { width: 1, height: 1, flex: 1, 'max-width': 1, 'max-height': 1 };

        // Props de TEXTO: ademas de destinosDeEstilo(), tambien van al <p>
        // de adentro si existe (ver extenderATexto). border/padding/
        // background/box-shadow NO estan en esta lista a proposito: esas
        // son "chrome" del boton, ponerlas tambien en el <p> duplicaria
        // bordes/relleno visualmente (dos rectangulos anidados).
        var PROPS_TEXTO = { 'font-size': 1, 'font-weight': 1, 'text-align': 1, 'text-decoration': 1, 'letter-spacing': 1, color: 1 };

        // Muchos widgets (st.button entre ellos) envuelven su label en
        // `[data-testid="stMarkdownContainer"] p`, y ESTE proyecto le fija
        // font-size/font-weight propios ahi (navegacion.py, los botones del
        // nav-rail: ver arquitectura.md regla #154) — un elemento con su
        // propio valor explicito no hereda el del padre, asi que aplicar
        // font-size al <button> redirigido no mueve un pixel el texto
        // visible. Si el <p> existe, tambien es destino de las props de
        // TEXTO (ademas del boton, no en su lugar: barato y sin efecto
        // visible cuando el boton no tiene un p con su propio override).
        function extenderATexto(destinos) {
            var out = [];
            destinos.forEach(function(d) {
                out.push(d);
                var p = d.querySelector && d.querySelector('[data-testid="stMarkdownContainer"] p');
                if (p && out.indexOf(p) === -1) out.push(p);
            });
            return out;
        }

        // Hallazgo real (no hipotetico): un boton con `transition: all
        // 0.15s` puede terminar con la propiedad SIN aplicar aunque el
        // inline style tenga !important y el valor correcto -- el
        // setInterval de sync() (150ms) REINICIA la transicion en cada
        // tick, casi a la par de su propia duracion, asi que nunca
        // termina de llegar al valor nuevo (se ve "trabado" en el
        // original, sin ningun error). Cortar la transicion es
        // obligatorio antes de tocar cualquier propiedad animable.
        function neutralizarTransicion(el) {
            el.style.setProperty('transition', 'none', 'important');
        }

        // CERO_ES_UN_VALOR (2026-08-21): `valor === null` significa "sacar el
        // override y volver a lo que dice estilos/", y los sliders lo usaban
        // para su minimo — radio 0, padding 0, borde 0, sombra 0. En una
        // herramienta que existe para PROBAR, el 0 de esos cuatro es
        // justamente lo que se quiere ver ("y si las esquinas fueran en
        // angulo?"): mandarlo a null hacia que arrastrar a 0 RESTAURARA el
        // valor del CSS (12px de radio, en el rail), o sea el sintoma exacto
        // de "el control no hace nada". Ahora 0 se aplica como 0px/none y
        // volver al original es lo que hace el boton "Ver original".
        function establecerCambioEstilo(elemento, registro, prop, valor) {
            var destinos = destinosDeEstilo(elemento);
            if (PROPS_TEXTO[prop]) destinos = extenderATexto(destinos);
            registro.transicionNeutralizada = true;
            destinos.forEach(neutralizarTransicion);
            if (valor === null) {
                delete registro.cambios[prop];
                destinos.forEach(function(d) { d.style.removeProperty(prop); });
            } else {
                registro.cambios[prop] = valor;
                destinos.forEach(function(d) { d.style.setProperty(prop, valor, 'important'); });
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
            // Geometria siempre sobre `elemento`; el resto sobre
            // destinosDeEstilo() (calculado una sola vez si hace falta).
            var destinos = null;
            if (registro.transicionNeutralizada) {
                destinos = destinosDeEstilo(elemento);
                neutralizarTransicion(elemento);
                destinos.forEach(neutralizarTransicion);
            }
            var destinosTexto = null;
            for (var prop in registro.cambios) {
                if (PROPS_GEOMETRIA[prop]) {
                    elemento.style.setProperty(prop, registro.cambios[prop], 'important');
                } else if (PROPS_TEXTO[prop]) {
                    if (!destinosTexto) {
                        if (!destinos) destinos = destinosDeEstilo(elemento);
                        destinosTexto = extenderATexto(destinos);
                    }
                    for (var dt = 0; dt < destinosTexto.length; dt++) {
                        destinosTexto[dt].style.setProperty(prop, registro.cambios[prop], 'important');
                    }
                } else {
                    if (!destinos) destinos = destinosDeEstilo(elemento);
                    for (var di = 0; di < destinos.length; di++) {
                        destinos[di].style.setProperty(prop, registro.cambios[prop], 'important');
                    }
                }
            }
            // Padding/tamaño de letra sobre un boton redirigido no crecen
            // nada por si solos: los botones de Streamlit traen
            // box-sizing:border-box con width/height EXPLICITOS, asi que
            // el padding se come espacio de adentro en vez de agrandar la
            // caja. Liberar a width/height:auto solo cuando de verdad se
            // esta tocando padding o font-size (nunca "porque hay botones
            // adentro" sin mas: eso correria en cada tick para cualquier
            // pin y podria desalinear pills que Streamlit iguala a
            // proposito con un width fijo).
            if (registro.cambios['padding'] !== undefined || registro.cambios['font-size'] !== undefined) {
                if (!destinos) destinos = destinosDeEstilo(elemento);
                if (destinos.length && destinos[0] !== elemento) {
                    for (var dj = 0; dj < destinos.length; dj++) {
                        destinos[dj].style.setProperty('width', 'auto', 'important');
                        destinos[dj].style.setProperty('height', 'auto', 'important');
                    }
                }
            }
            aplicarTransform(elemento, registro);
        }

        // ---- arrastre: resize (bordes/esquina) y mover (nudge) ----
        function iniciarArrastre(e, modo) {
            e.preventDefault();
            e.stopPropagation();
            var ctx = elementoActivo();
            if (!ctx) return;
            // transition:all puede pelear con el arrastre igual que con los
            // controles de estilo (ver neutralizarTransicion) — un resize u
            // "nudge" también se ve trabado sin esto si el elemento anima.
            ctx.registro.transicionNeutralizada = true;
            neutralizarTransicion(ctx.el);
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

        // `onRevertir`, si se pasa, agrega un "↺" junto a la etiqueta que
        // saca SOLO esta propiedad (vuelve a lo que dice estilos/) sin
        // tocar el resto de los cambios — "Ver original" abajo del panel
        // sigue siendo el A/B de TODO junto; esto es por fila.
        function filaControl(etiquetaTexto, controlEl, valorEl, onRevertir) {
            var div = doc.createElement('div');
            div.style.cssText = 'margin:12px 0';
            var lbl = doc.createElement('div');
            lbl.style.cssText = 'font-size:11px;color:#8b8b95;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center';
            var izq = doc.createElement('span');
            izq.style.cssText = 'display:flex;align-items:center;gap:5px';
            var txt = doc.createElement('span');
            txt.textContent = etiquetaTexto;
            izq.appendChild(txt);
            if (onRevertir) {
                var btnRev = doc.createElement('button');
                btnRev.textContent = '↺';
                btnRev.title = 'Revertir esta propiedad a estilos/';
                btnRev.style.cssText = 'background:transparent;color:#6f6f7a;border:0;padding:0;font-size:12px;line-height:1;cursor:pointer';
                btnRev.addEventListener('click', function(ev) { ev.stopPropagation(); onRevertir(); });
                izq.appendChild(btnRev);
            }
            lbl.appendChild(izq);
            lbl.appendChild(valorEl);
            div.appendChild(lbl);
            div.appendChild(controlEl);
            return div;
        }

        var SOMBRAS = ['', '0 1px 3px rgba(16,16,20,.14)', '0 4px 10px rgba(16,16,20,.18)',
                       '0 8px 20px rgba(16,16,20,.22)', '0 16px 34px rgba(16,16,20,.28)'];

        function seccion(titulo) {
            var div = doc.createElement('div');
            div.style.cssText = 'font-size:10px;letter-spacing:.04em;color:#6f6f7a;text-transform:uppercase;margin:16px 0 4px;padding-top:10px;border-top:1px solid #2a2a35';
            div.textContent = titulo;
            return div;
        }

        // `opciones.transparente` agrega un swatch a cuadros (no hay forma de
        // "pintar" transparente en un swatch solido) que manda 'transparent'
        // — antes no existia manera de probar "sacale el fondo a la
        // tarjeta". `opciones.libre` agrega un <input type=color> igual al
        // que ya tenia Borde completo, para no limitar Texto/Fondo a los
        // 16 tonos fijos de PALETA.
        function construirSwatches(valorActual, onPick, opciones) {
            opciones = opciones || {};
            var wrap = doc.createElement('div');
            wrap.style.cssText = 'display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin-top:6px';
            var botones = [];
            var actualNorm = (valorActual || '').toLowerCase();
            function marcar(b) {
                botones.forEach(function(x) { x.style.outline = ''; });
                b.style.outline = '2px solid #fff';
                b.style.outlineOffset = '1px';
            }
            PALETA.forEach(function(c) {
                var b = doc.createElement('button');
                b.title = c.nombre;
                var seleccionado = c.hex.toLowerCase() === actualNorm;
                b.style.cssText = 'width:20px;height:20px;border-radius:4px;border:0;padding:0;cursor:pointer;background:' + c.hex
                    + (seleccionado ? ';outline:2px solid #fff;outline-offset:1px' : '');
                b.addEventListener('click', function() {
                    marcar(b);
                    onPick(c.hex);
                });
                botones.push(b);
                wrap.appendChild(b);
            });
            if (opciones.transparente) {
                var bT = doc.createElement('button');
                bT.title = 'Transparente';
                bT.style.cssText = 'width:20px;height:20px;border-radius:4px;border:1px solid #34343f;padding:0;cursor:pointer;background-color:#1c1c24;'
                    + 'background-image:linear-gradient(45deg,#3a3a44 25%,transparent 25%),linear-gradient(-45deg,#3a3a44 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#3a3a44 75%),linear-gradient(-45deg,transparent 75%,#3a3a44 75%);'
                    + 'background-size:8px 8px;background-position:0 0,0 4px,4px -4px,-4px 0px'
                    + (actualNorm === 'transparent' ? ';outline:2px solid #fff;outline-offset:1px' : '');
                bT.addEventListener('click', function() {
                    marcar(bT);
                    onPick('transparent');
                });
                botones.push(bT);
                wrap.appendChild(bT);
            }
            if (opciones.libre) {
                var inpLibre = doc.createElement('input');
                inpLibre.type = 'color';
                // <input type=color> exige un #rrggbb valido — 'transparent'
                // o 'sin cambio' (null) no sirven de semilla, cae a un
                // neutral en vez de reventar con un valor invalido.
                inpLibre.value = /^#[0-9a-f]{6}$/i.test(valorActual || '') ? valorActual : '#6c5ce7';
                inpLibre.title = 'Elegir cualquier color';
                inpLibre.style.cssText = 'width:20px;height:20px;border:0;border-radius:4px;padding:0;cursor:pointer;background:transparent';
                inpLibre.addEventListener('input', function() {
                    botones.forEach(function(x) { x.style.outline = ''; });
                    onPick(inpLibre.value);
                });
                wrap.appendChild(inpLibre);
            }
            return wrap;
        }

        // ---- copiar CSS: cerrar el circuito previsualizar -> estilos/ ----
        // Hasta aca el panel sabia MOSTRAR una vista previa pero no sabia
        // ENTREGARLA: bajar 6 cambios a estilos/ era leerlos a ojo del
        // panel y dictarlos. registro.cambios ya tiene todo lo que hace
        // falta — esto solo lo junta y lo formatea.
        function fusionar(a, b) {
            var out = {};
            Object.keys(a).forEach(function(k) { out[k] = a[k]; });
            Object.keys(b).forEach(function(k) { out[k] = b[k]; });
            return out;
        }

        function construirBloqueCSS(key, elemento, registro, sub) {
            // Con sub-pin el selector baja al hijo: `.cp-rank-tit` es una
            // clase de autor y pegar `div[class*="st-key-K"] .cp-rank-tit`
            // en estilos/ hace exactamente lo que se vio en pantalla. Sin
            // esto el bloque copiado moveria la tarjeta entera — el mismo
            // "pegarlo no hace lo que probe" que motivo la regla #154.
            var ancla = 'div[class*="st-key-' + key + '"]' + (sub ? ' .' + sub : '');
            var destinos = destinosDeEstilo(elemento);
            var redirigido = destinos[0] !== elemento;
            // Mismo criterio que destinosDeEstilo: pills de un stButtonGroup
            // comparten selector de grupo; un boton/popover suelto, no.
            var selEstilo = !redirigido ? ancla
                : (elemento.querySelector('[data-testid="stButtonGroup"] button')
                    ? ancla + ' [data-testid="stButtonGroup"] button'
                    : ancla + ' button');
            // Mismo criterio que extenderATexto en runtime: si el destino de
            // estilo tiene su propio <p> de label (navegacion.py se lo fija
            // a los botones del nav-rail — arquitectura.md regla #154), las
            // props de TEXTO van a ESE selector. Pegar el bloque con el
            // selector del boton se veria "no hace nada" — el mismo bug que
            // motivo este agregado.
            var hayTextoPropio = destinos.some(function(d) {
                return d.querySelector && d.querySelector('[data-testid="stMarkdownContainer"] p');
            });
            var selTexto = hayTextoPropio ? ancla + ' [data-testid="stMarkdownContainer"] p' : selEstilo;

            var geo = {}, estBoton = {}, estTexto = {};
            Object.keys(registro.cambios).forEach(function(prop) {
                if (PROPS_GEOMETRIA[prop]) { geo[prop] = registro.cambios[prop]; }
                else if (PROPS_TEXTO[prop]) { estTexto[prop] = registro.cambios[prop]; }
                else { estBoton[prop] = registro.cambios[prop]; }
            });
            var t = registro.transformState;
            if (t.translateX || t.translateY || t.rotateDeg) {
                // El mover/rotar siempre va sobre el elemento mismo (igual
                // que aplicarTransform), nunca redirigido.
                geo.transform = 'translate(' + t.translateX + 'px,' + t.translateY + 'px) rotate(' + t.rotateDeg + 'deg)';
            }

            // Agrupar por selector (no por grupo geo/boton/texto): cuando
            // dos grupos terminan en el MISMO selector (el caso comun, sin
            // redireccion) se funden en un solo bloque en vez de salir
            // duplicados.
            var grupos = {};
            function sumar(sel, props) {
                if (!Object.keys(props).length) return;
                grupos[sel] = fusionar(grupos[sel] || {}, props);
            }
            sumar(ancla, geo);
            sumar(selEstilo, estBoton);
            sumar(selTexto, estTexto);

            var bloques = [];
            Object.keys(grupos).forEach(function(sel) {
                var props = grupos[sel];
                var lineas = Object.keys(props).map(function(p) { return '    ' + p + ': ' + props[p] + ';'; });
                bloques.push(sel + ' {\\n' + lineas.join('\\n') + '\\n}');
            });
            if (!bloques.length) return null;

            var notas = [];
            if (redirigido) notas.push('caja redirigida a los botones internos');
            if (hayTextoPropio) notas.push('texto redirigido al <p> del label, que trae su propio font-size/weight');
            var pie = notas.length
                ? '\\n/* ' + notas.join(' — ') + ' — ver destinosDeEstilo()/extenderATexto() en _diseno_js.py */'
                : '';

            var encabezado = '/* copiado del modo diseño — ' + key + (sub ? ' .' + sub : '') + ' */';
            return encabezado + '\\n' + bloques.join('\\n\\n') + pie;
        }

        // Duplica (a proposito, ver docstring de diseno.py) el fallback de
        // copiarTexto() de _inspector_js.py: este script corre en OTRO
        // iframe de components.html, sin acceso a esa funcion local.
        function copiarTextoDiseno(texto, cb) {
            var terminado = false;
            var marcar = function(ok) { if (!terminado) { terminado = true; cb(ok); } };
            function fallback() {
                if (terminado) return;
                var ta = doc.createElement('textarea');
                ta.value = texto;
                ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;opacity:0';
                doc.body.appendChild(ta);
                ta.focus(); ta.select();
                var ok = false;
                try { ok = doc.execCommand('copy'); } catch(_) {}
                doc.body.removeChild(ta);
                marcar(ok);
            }
            if (win.navigator.clipboard && win.navigator.clipboard.writeText && win.isSecureContext) {
                try {
                    win.navigator.clipboard.writeText(texto).then(function() { marcar(true); }, fallback);
                    setTimeout(function() { if (!terminado) fallback(); }, 300);
                    return;
                } catch(_) {}
            }
            fallback();
        }

        // `res` es el objeto de elementoPineado() entero (key + sub + el),
        // no la key suelta: el arbol necesita saber si el actual es el
        // contenedor o un hijo suyo, y "Copiar CSS" necesita el sub.
        function construirControles(res, registro) {
            var key = res.key;
            var elemento = res.el;
            panel.style.cssText = PANEL_CSS_EXPANDIDO;
            panel.style.display = 'block';
            panel.onclick = null;
            panel.innerHTML = '';

            var header = doc.createElement('div');
            header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #2a2a35';
            var headerKey = doc.createElement('div');
            headerKey.style.cssText = 'font-size:11px;color:#9385ec;word-break:break-all;font-family:"Courier New",monospace;flex:1;min-width:0';
            headerKey.textContent = res.sub ? (key + ' .' + res.sub) : key;
            var btnSoltar = doc.createElement('button');
            btnSoltar.textContent = 'Soltar';
            btnSoltar.style.cssText = 'background:#2A2A35;color:#fff;border:0;border-radius:4px;padding:4px 8px;font:600 11px sans-serif;cursor:pointer;flex:0 0 auto';
            btnSoltar.addEventListener('click', function() {
                if (win.__inspectorTogglePin) win.__inspectorTogglePin(true);
            });
            // Ocultar el contorno SIN soltar el pin: separarlo 4px alcanza
            // para ver el borde, pero para juzgar color/sombra/el look final
            // hace falta la vista limpia — y soltar el pin obligaba a volver
            // a fijarlo para seguir editando (regla #166).
            var btnContorno = doc.createElement('button');
            btnContorno.title = 'Ocultar/mostrar el contorno de seleccion (el pin no se suelta)';
            btnContorno.textContent = win.__disenoContornoOculto ? '□' : '▣';
            btnContorno.style.cssText = 'background:#2A2A35;color:#fff;border:0;border-radius:4px;padding:4px 7px;font:600 11px sans-serif;cursor:pointer;flex:0 0 auto';
            btnContorno.addEventListener('click', function() {
                win.__disenoContornoOculto = !win.__disenoContornoOculto;
                btnContorno.textContent = win.__disenoContornoOculto ? '□' : '▣';
                overlay.style.display = win.__disenoContornoOculto ? 'none' : 'block';
            });

            header.appendChild(headerKey);
            header.appendChild(btnContorno);
            header.appendChild(botonColapsar());
            header.appendChild(btnSoltar);
            panel.appendChild(header);

            // Jerarquía: árbol vertical, RAÍZ primero (inverso de
            // cadenaKeysDiseno, que camina de la hoja al body) — se lee de
            // arriba hacia abajo como el anidamiento real en el código,
            // a diferencia de las migas horizontales del inspector
            // (elemento -> raíz). Un clic en cualquier ancestro salta el
            // pin ahí sin tener que ubicarlo a ojo en la pantalla.
            var cadenaDiseno = cadenaKeysDiseno(elemento).slice().reverse();
            // Hojas SIN key: hijos con clase de autor del widget pineado. Son
            // el unico camino para bajar el pin a un `st.markdown` con HTML
            // propio — la razon por la que el arbol tambien se dibuja cuando
            // la cadena tiene un solo eslabon.
            var hojasSub = hijosConClasePropia(key);
            if (res.sub && hojasSub.indexOf(res.sub) === -1) hojasSub.unshift(res.sub);
            if (cadenaDiseno.length > 1 || hojasSub.length) {
                var arbolBox = doc.createElement('div');
                arbolBox.style.cssText = 'margin-bottom:10px;padding:8px 9px;background:#1c1c24;border:1px solid #2a2a35;border-radius:6px;overflow-x:auto';
                cadenaDiseno.forEach(function(k, i) {
                    // Con un sub activo el "actual" es la hoja, no su
                    // contenedor: la fila de la key queda clicable a
                    // proposito, y ese clic es el camino de vuelta.
                    var esActual = (k === key && !res.sub);
                    var fila = doc.createElement('div');
                    fila.style.cssText = 'display:flex;align-items:center;gap:4px;padding:2px 0;padding-left:' + (i * 11) + 'px;white-space:nowrap';
                    if (i > 0) {
                        var rama = doc.createElement('span');
                        rama.textContent = '└';
                        rama.style.cssText = 'color:#3f3f4c;flex-shrink:0;font-size:11px';
                        fila.appendChild(rama);
                    }
                    var nodo = doc.createElement(esActual ? 'span' : 'button');
                    nodo.textContent = k;
                    nodo.style.cssText = 'font:11px "Courier New",monospace;background:transparent;border:0;padding:1px 3px;border-radius:3px;'
                        + 'color:' + (esActual ? '#e4e4e8' : '#9385ec') + ';'
                        + 'font-weight:' + (esActual ? '700' : '400')
                        + (esActual ? '' : ';cursor:pointer');
                    if (!esActual) {
                        nodo.addEventListener('mouseenter', function() { nodo.style.background = '#2A2A35'; });
                        nodo.addEventListener('mouseleave', function() { nodo.style.background = 'transparent'; });
                        nodo.addEventListener('click', function() { saltarADiseno(k); });
                    }
                    fila.appendChild(nodo);
                    arbolBox.appendChild(fila);
                });
                hojasSub.forEach(function(c) {
                    var esActualSub = (c === res.sub);
                    var fila = doc.createElement('div');
                    fila.style.cssText = 'display:flex;align-items:center;gap:4px;padding:2px 0;padding-left:'
                        + (cadenaDiseno.length * 11) + 'px;white-space:nowrap';
                    var rama = doc.createElement('span');
                    rama.textContent = '└';
                    rama.style.cssText = 'color:#3f3f4c;flex-shrink:0;font-size:11px';
                    fila.appendChild(rama);
                    var nodo = doc.createElement(esActualSub ? 'span' : 'button');
                    nodo.textContent = '.' + c;
                    nodo.title = 'Bajar el pin a este hijo (no tiene key propia)';
                    nodo.style.cssText = 'font:11px "Courier New",monospace;background:transparent;border:0;padding:1px 3px;border-radius:3px;'
                        + 'color:' + (esActualSub ? '#e4e4e8' : '#7fb2e5') + ';'
                        + 'font-weight:' + (esActualSub ? '700' : '400')
                        + (esActualSub ? '' : ';cursor:pointer');
                    if (!esActualSub) {
                        nodo.addEventListener('mouseenter', function() { nodo.style.background = '#2A2A35'; });
                        nodo.addEventListener('mouseleave', function() { nodo.style.background = 'transparent'; });
                        nodo.addEventListener('click', function() { bajarASub(c); });
                    }
                    fila.appendChild(nodo);
                    arbolBox.appendChild(fila);
                });
                panel.appendChild(arbolBox);
            }

            // Fila propia y arriba de todo a propósito: es la accion que
            // cierra el circuito (previsualizar -> bajarlo a estilos/) y
            // conviene que este a mano sin scrollear el panel entero.
            var filaCopiar = doc.createElement('div');
            filaCopiar.style.cssText = 'margin-bottom:10px;display:flex;gap:6px;align-items:center';
            var btnCopiarCSS = doc.createElement('button');
            btnCopiarCSS.textContent = '📋 Copiar CSS';
            btnCopiarCSS.style.cssText = 'flex:1;background:#3C3489;color:#fff;border:0;border-radius:4px;padding:7px;font:600 11px sans-serif;cursor:pointer';
            var estadoCopiar = spanValor('');
            estadoCopiar.style.fontSize = '10px';
            // Fallback manual, oculto hasta que haga falta: si el automatico
            // falla (frecuente en Streamlit Cloud, el iframe anidado de
            // components.html — arquitectura.md § Reglas #39) no hay nada
            // mas en pantalla para seleccionar, a diferencia del inspector
            // que ya tiene su <pre> visible. Sin este textarea, "Ctrl+C"
            // seria un mensaje que miente.
            var taManual = doc.createElement('textarea');
            taManual.readOnly = true;
            taManual.style.cssText = 'display:none;width:100%;height:90px;margin-top:6px;background:#1c1c24;color:#e4e4e8;border:1px solid #34343f;border-radius:4px;padding:6px;font:10px/1.4 "Courier New",monospace;box-sizing:border-box';
            btnCopiarCSS.addEventListener('click', function() {
                var ctx = elementoActivo();
                var bloque = ctx ? construirBloqueCSS(ctx.key, ctx.el, ctx.registro, ctx.sub) : null;
                if (!bloque) {
                    estadoCopiar.textContent = 'nada que copiar';
                    estadoCopiar.style.color = '#8b8b95';
                    taManual.style.display = 'none';
                    return;
                }
                copiarTextoDiseno(bloque, function(ok) {
                    estadoCopiar.textContent = ok ? 'copiado ✓' : 'automático bloqueado: seleccionado abajo';
                    estadoCopiar.style.color = ok ? '#74ab7e' : '#f0997b';
                    if (ok) {
                        taManual.style.display = 'none';
                    } else {
                        taManual.value = bloque;
                        taManual.style.display = 'block';
                        taManual.focus();
                        taManual.select();
                    }
                });
            });
            filaCopiar.appendChild(btnCopiarCSS);
            filaCopiar.appendChild(estadoCopiar);
            panel.appendChild(filaCopiar);
            panel.appendChild(taManual);

            // Para LEER valores iniciales/computados, usar el mismo destino
            // al que van a ESCRIBIR los controles de estilo — si no, el
            // slider arranca mostrando el radio/tamaño de un wrapper
            // invisible en vez del boton real que se ve en pantalla.
            var destinos = destinosDeEstilo(elemento);
            var lectura = destinos[0];
            // Idem para TEXTO, un nivel mas adentro (ver extenderATexto):
            // si no, "Tamaño de letra" arranca mostrando el font-size del
            // <button> (16px, el default del navegador) en vez del <p> que
            // en realidad se ve en pantalla (13.5px, fijado por
            // navegacion.py) — el slider parece "no hacer nada" porque
            // arranca leyendo el numero equivocado.
            var destinosTexto = extenderATexto(destinos);
            var lecturaTexto = destinosTexto[destinosTexto.length - 1];

            // El contorno violeta marca SIEMPRE el elemento pineado, pero
            // los controles de ESTILO pueden escribir en otro lado. Decirlo
            // aca: si no, el unico sintoma es un cambio que aparece donde
            // no se esperaba, y nada en pantalla explica por que.
            if (lectura !== elemento) {
                var aviso = doc.createElement('div');
                aviso.style.cssText = 'font:11px/1.4 -apple-system,sans-serif;color:#9385ec;background:#1c1c24;border:1px solid #34343f;border-radius:4px;padding:6px 7px;margin-bottom:10px';
                aviso.textContent = 'Estilo → ' + destinos.length
                    + (destinos.length > 1 ? ' botones internos' : ' botón interno')
                    + '. Tamaño y posición → el contorno.';
                panel.appendChild(aviso);
            }
            // Un nivel mas adentro que el aviso de arriba: el LABEL (texto)
            // puede vivir en su propio <p> con font-size/weight fijados
            // aparte del boton (arquitectura.md regla #154) — sin decirlo
            // ahi, "Tamaño de letra" parece no hacer nada aunque el inline
            // este aplicado y confirmado en el boton.
            if (lecturaTexto !== lectura) {
                var avisoTexto = doc.createElement('div');
                avisoTexto.style.cssText = 'font:11px/1.4 -apple-system,sans-serif;color:#9385ec;background:#1c1c24;border:1px solid #34343f;border-radius:4px;padding:6px 7px;margin-bottom:10px';
                avisoTexto.textContent = 'Tipografía/color de texto → el <p> del label (trae su propio tamaño/peso), no el botón.';
                panel.appendChild(avisoTexto);
            }

            if (esMock(key)) {
                var avisoMock = doc.createElement('div');
                avisoMock.style.cssText = 'font:11px/1.4 -apple-system,sans-serif;color:#e4e4e8;background:#1c1c24;border:1px dashed #6c5ce7;border-radius:4px;padding:6px 7px;margin-bottom:10px';
                avisoMock.textContent = 'Insertado por el modo diseño: no existe en el código ni en estilos/. Se va al recargar.';
                panel.appendChild(avisoMock);
            }

            var tamVal = spanValor('');
            panel.appendChild(filaSoloLectura('Tamaño', tamVal));
            var posVal = spanValor('');
            panel.appendChild(filaSoloLectura('Posición (nudge)', posVal));
            panel.__tamVal = tamVal;
            panel.__posVal = posVal;

            // radio de borde
            var radioVal = registro.cambios['border-radius']
                ? numDe(registro.cambios['border-radius'], 0)
                : numDe(win.getComputedStyle(lectura).borderTopLeftRadius, 0);
            var inpRadio = rango(0, 32, 1, radioVal);
            var radioLbl = spanValor(Math.round(radioVal) + 'px');
            inpRadio.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpRadio.value, 10);
                radioLbl.textContent = v + 'px';
                // 0 se APLICA como 0px, no se traduce a "sacar el override".
                // Ver el comentario de CERO_ES_UN_VALOR mas abajo.
                establecerCambioEstilo(ctx.el, ctx.registro, 'border-radius', v + 'px');
            });
            panel.appendChild(filaControl('Radio de borde', inpRadio, radioLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'border-radius', null);
                rehacerPanel();
            }));

            // padding (uniforme)
            var padVal = registro.cambios['padding']
                ? numDe(registro.cambios['padding'], 0)
                : numDe(win.getComputedStyle(lectura).paddingTop, 0);
            var inpPad = rango(0, 48, 1, padVal);
            var padLbl = spanValor(Math.round(padVal) + 'px');
            inpPad.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpPad.value, 10);
                padLbl.textContent = v + 'px';
                establecerCambioEstilo(ctx.el, ctx.registro, 'padding', v + 'px');
            });
            panel.appendChild(filaControl('Padding', inpPad, padLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'padding', null);
                rehacerPanel();
            }));

            // margen (uniforme) — hermano de padding, mismo tratamiento;
            // pedido explicito: "un poco mas de aire arriba" es el ajuste
            // mas comun de todos y no habia forma de probarlo en vivo.
            var margVal = registro.cambios['margin']
                ? numDe(registro.cambios['margin'], 0)
                : numDe(win.getComputedStyle(lectura).marginTop, 0);
            var inpMarg = rango(0, 48, 1, margVal);
            var margLbl = spanValor(Math.round(margVal) + 'px');
            inpMarg.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpMarg.value, 10);
                margLbl.textContent = v + 'px';
                establecerCambioEstilo(ctx.el, ctx.registro, 'margin', v + 'px');
            });
            panel.appendChild(filaControl('Margen', inpMarg, margLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'margin', null);
                rehacerPanel();
            }));

            // borde completo (ancho + color -> shorthand 'border')
            var inpBordeAncho = rango(0, 8, 1, registro.bordeAncho);
            var bordeLbl = spanValor(registro.bordeAncho + 'px');
            var inpBordeColor = doc.createElement('input');
            inpBordeColor.type = 'color';
            inpBordeColor.value = registro.bordeColor;
            inpBordeColor.style.cssText = 'width:100%;height:24px;border:0;border-radius:4px;padding:0;cursor:pointer;margin-top:8px;background:transparent';
            function aplicarBorde(ctx) {
                establecerCambioEstilo(ctx.el, ctx.registro, 'border',
                    ctx.registro.bordeAncho === 0 ? 'none'
                        : (ctx.registro.bordeAncho + 'px solid ' + ctx.registro.bordeColor));
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
            bordeWrap.appendChild(construirSwatches(registro.bordeColor, function(hex) {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.bordeColor = hex;
                inpBordeColor.value = hex;
                aplicarBorde(ctx);
            }));
            bordeWrap.appendChild(inpBordeColor);
            panel.appendChild(filaControl('Borde completo', bordeWrap, bordeLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.bordeAncho = 0;
                establecerCambioEstilo(ctx.el, ctx.registro, 'border', null);
                rehacerPanel();
            }));

            // sombra
            var inpSombra = rango(0, 4, 1, registro.sombraNivel);
            var sombraLbl = spanValor(registro.sombraNivel === 0 ? 'sin sombra' : ('nivel ' + registro.sombraNivel));
            inpSombra.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.sombraNivel = parseInt(inpSombra.value, 10);
                sombraLbl.textContent = ctx.registro.sombraNivel === 0 ? 'sin sombra' : ('nivel ' + ctx.registro.sombraNivel);
                establecerCambioEstilo(ctx.el, ctx.registro, 'box-shadow',
                    ctx.registro.sombraNivel === 0 ? 'none' : SOMBRAS[ctx.registro.sombraNivel]);
            });
            panel.appendChild(filaControl('Sombra', inpSombra, sombraLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.sombraNivel = 0;
                establecerCambioEstilo(ctx.el, ctx.registro, 'box-shadow', null);
                rehacerPanel();
            }));

            // ---- tipografía ----
            panel.appendChild(seccion('Tipografía'));

            var fsVal = registro.cambios['font-size']
                ? numDe(registro.cambios['font-size'], 14)
                : numDe(win.getComputedStyle(lecturaTexto).fontSize, 14);
            var inpFs = rango(10, 32, 1, fsVal);
            var fsLbl = spanValor(Math.round(fsVal) + 'px');
            inpFs.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpFs.value, 10);
                fsLbl.textContent = v + 'px';
                establecerCambioEstilo(ctx.el, ctx.registro, 'font-size', v + 'px');
            });
            panel.appendChild(filaControl('Tamaño de letra', inpFs, fsLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'font-size', null);
                rehacerPanel();
            }));

            var PESOS = [['400', 'Normal'], ['600', 'Semibold'], ['700', 'Bold']];
            var pesoWrap = doc.createElement('div');
            pesoWrap.style.cssText = 'display:flex;gap:4px;margin-top:6px';
            var pesoBotones = [];
            var pesoActual = registro.cambios['font-weight'] || String(numDe(win.getComputedStyle(lecturaTexto).fontWeight, 400));
            PESOS.forEach(function(par) {
                var b = doc.createElement('button');
                b.textContent = par[1];
                b.style.cssText = 'flex:1;background:' + (par[0] === pesoActual ? '#3C3489' : '#1c1c24') + ';color:#fff;border:1px solid #34343f;border-radius:4px;padding:5px 2px;font:11px sans-serif;cursor:pointer';
                b.addEventListener('click', function() {
                    var ctx = elementoActivo(); if (!ctx) return;
                    establecerCambioEstilo(ctx.el, ctx.registro, 'font-weight', par[0]);
                    pesoBotones.forEach(function(x) { x.style.background = '#1c1c24'; });
                    b.style.background = '#3C3489';
                });
                pesoBotones.push(b);
                pesoWrap.appendChild(b);
            });
            panel.appendChild(filaControl('Peso', pesoWrap, spanValor('')));

            var ALINEACIONES = [['left', 'Izq'], ['center', 'Centro'], ['right', 'Der']];
            var alinWrap = doc.createElement('div');
            alinWrap.style.cssText = 'display:flex;gap:4px;margin-top:6px';
            var alinBotones = [];
            var alinActual = registro.cambios['text-align'] || win.getComputedStyle(lecturaTexto).textAlign;
            ALINEACIONES.forEach(function(par) {
                var b = doc.createElement('button');
                b.textContent = par[1];
                b.style.cssText = 'flex:1;background:' + (par[0] === alinActual ? '#3C3489' : '#1c1c24') + ';color:#fff;border:1px solid #34343f;border-radius:4px;padding:5px 2px;font:11px sans-serif;cursor:pointer';
                b.addEventListener('click', function() {
                    var ctx = elementoActivo(); if (!ctx) return;
                    establecerCambioEstilo(ctx.el, ctx.registro, 'text-align', par[0]);
                    alinBotones.forEach(function(x) { x.style.background = '#1c1c24'; });
                    b.style.background = '#3C3489';
                });
                alinBotones.push(b);
                alinWrap.appendChild(b);
            });
            panel.appendChild(filaControl('Alineación', alinWrap, spanValor('')));

            var subrayadoActivo = (registro.cambios['text-decoration'] === 'underline');
            var btnSubrayado = doc.createElement('button');
            btnSubrayado.style.cssText = 'width:100%;color:#fff;border:1px solid #34343f;border-radius:4px;padding:6px;font:11px sans-serif;cursor:pointer;margin-top:6px';
            function pintarSubrayado() {
                btnSubrayado.textContent = subrayadoActivo ? 'Subrayado: on' : 'Subrayado: off';
                btnSubrayado.style.background = subrayadoActivo ? '#3C3489' : '#1c1c24';
            }
            pintarSubrayado();
            btnSubrayado.addEventListener('click', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                subrayadoActivo = !subrayadoActivo;
                establecerCambioEstilo(ctx.el, ctx.registro, 'text-decoration', subrayadoActivo ? 'underline' : 'none');
                pintarSubrayado();
            });
            panel.appendChild(filaControl('Subrayado', btnSubrayado, spanValor('')));

            var lsVal = registro.cambios['letter-spacing'] ? numDe(registro.cambios['letter-spacing'], 0) : 0;
            var inpLs = rango(-1, 6, 0.5, lsVal);
            var lsLbl = spanValor(lsVal + 'px');
            inpLs.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseFloat(inpLs.value);
                lsLbl.textContent = v + 'px';
                establecerCambioEstilo(ctx.el, ctx.registro, 'letter-spacing', v + 'px');
            });
            panel.appendChild(filaControl('Espaciado entre letras', inpLs, lsLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'letter-spacing', null);
                rehacerPanel();
            }));

            var inpRot = rango(-45, 45, 1, registro.transformState.rotateDeg);
            var rotLbl = spanValor(registro.transformState.rotateDeg + '°');
            inpRot.addEventListener('input', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                var v = parseInt(inpRot.value, 10);
                rotLbl.textContent = v + '°';
                ctx.registro.transformState.rotateDeg = v;
                aplicarTransform(ctx.el, ctx.registro);
            });
            panel.appendChild(filaControl('Rotar (orientación)', inpRot, rotLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                ctx.registro.transformState.rotateDeg = 0;
                aplicarTransform(ctx.el, ctx.registro);
                rehacerPanel();
            }));

            // ---- color por rol ----
            panel.appendChild(seccion('Color'));

            var colorTextoActual = registro.cambios['color'] || null;
            var colorTextoLbl = spanValor(colorTextoActual || 'sin cambio');
            panel.appendChild(filaControl('Texto', construirSwatches(colorTextoActual, function(hex) {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'color', hex);
                colorTextoLbl.textContent = hex;
            }, { libre: true }), colorTextoLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'color', null);
                rehacerPanel();
            }));

            var colorFondoActual = registro.cambios['background-color'] || null;
            var colorFondoLbl = spanValor(colorFondoActual || 'sin cambio');
            panel.appendChild(filaControl('Fondo', construirSwatches(colorFondoActual, function(hex) {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'background-color', hex);
                colorFondoLbl.textContent = hex;
            }, { libre: true, transparente: true }), colorFondoLbl, function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'background-color', null);
                rehacerPanel();
            }));

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

            // ---- insertar: elementos de mentira ----
            panel.appendChild(seccion('Insertar'));

            var POSICIONES = [['antes', 'Antes'], ['dentro', 'Dentro'], ['despues', 'Después']];
            var posWrap = doc.createElement('div');
            posWrap.style.cssText = 'display:flex;gap:4px;margin-top:6px';
            var posBotones = [];
            POSICIONES.forEach(function(par) {
                var b = doc.createElement('button');
                b.textContent = par[1];
                b.style.cssText = 'flex:1;background:' + (par[0] === win.__disenoState.mockPos ? '#3C3489' : '#1c1c24') + ';color:#fff;border:1px solid #34343f;border-radius:4px;padding:5px 2px;font:11px sans-serif;cursor:pointer';
                b.addEventListener('click', function() {
                    win.__disenoState.mockPos = par[0];
                    posBotones.forEach(function(x) { x.style.background = '#1c1c24'; });
                    b.style.background = '#3C3489';
                });
                posBotones.push(b);
                posWrap.appendChild(b);
            });
            panel.appendChild(filaControl('Dónde (respecto del contorno)', posWrap, spanValor('')));

            var addWrap = doc.createElement('div');
            addWrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;margin-top:6px';
            TIPOS_MOCK.forEach(function(par) {
                var b = doc.createElement('button');
                b.textContent = '+ ' + par[1];
                b.style.cssText = 'flex:1 1 46%;background:#1c1c24;color:#fff;border:1px solid #34343f;border-radius:4px;padding:6px 2px;font:11px sans-serif;cursor:pointer';
                b.addEventListener('click', function() { agregarMock(par[0]); });
                addWrap.appendChild(b);
            });
            panel.appendChild(filaControl('Agregar', addWrap, spanValor('')));

            // Quitar: el que esta fijado (si es un mock) y el resto. Ambos
            // fuerzan la reconstruccion del panel porque cambia el conteo,
            // y la key fijada no cambia -> sync() sola no lo redibujaria.
            function rehacerPanel() {
                panel.dataset.builtForKey = '';
                sync();
            }

            if (esMock(key)) {
                var btnQuitarEste = doc.createElement('button');
                btnQuitarEste.textContent = 'Quitar este';
                btnQuitarEste.style.cssText = 'width:100%;margin-top:8px;background:#1c1c24;color:#e4e4e8;border:1px solid #34343f;border-radius:4px;padding:7px;font:11px sans-serif;cursor:pointer';
                btnQuitarEste.addEventListener('click', function() {
                    quitarMock(key);
                    if (win.__inspectorTogglePin) win.__inspectorTogglePin(true);
                    rehacerPanel();
                });
                panel.appendChild(btnQuitarEste);
            }

            var nMocks = win.__disenoState.mocks.length;
            if (nMocks) {
                var btnLimpiar = doc.createElement('button');
                btnLimpiar.textContent = nMocks === 1 ? 'Quitar el insertado'
                                                      : ('Quitar los ' + nMocks + ' insertados');
                btnLimpiar.style.cssText = 'width:100%;margin-top:6px;background:#1c1c24;color:#8b8b95;border:1px solid #34343f;border-radius:4px;padding:7px;font:11px sans-serif;cursor:pointer';
                btnLimpiar.addEventListener('click', function() {
                    var pineadoEraMock = esMock(key);
                    win.__disenoState.mocks.slice().forEach(function(m) { quitarMock(m.key); });
                    if (pineadoEraMock && win.__inspectorTogglePin) win.__inspectorTogglePin(true);
                    rehacerPanel();
                });
                panel.appendChild(btnLimpiar);
            }
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
            // Antes de resolver el pin: un mock puede SER el pineado, y
            // Streamlit se lo lleva cuando re-renderiza su rama.
            reponerMocks();
            var res = elementoPineado();

            // Panel: colapsado se ve igual (una pill chica) haya o no algo
            // pineado. El overlay/manijas del elemento pineado (mas abajo)
            // son independientes de esto — colapsar el panel no las apaga.
            if (win.__disenoState.panelColapsado) {
                pintarPill();
            } else if (!res) {
                panelEspera();
            } else if (!res.el) {
                panelPerdido(res.id);
            } else {
                if (panel.dataset.builtForKey !== res.id) {
                    construirControles(res, registroPara(res.id));
                    panel.dataset.builtForKey = res.id;
                }
                panel.style.display = 'block';
            }

            if (!res || !res.el) {
                overlay.style.display = 'none';
                return;
            }
            // Por `id`, no por key: la tarjeta y cada uno de sus hijos
            // pineables llevan su propio registro de cambios.
            var registro = registroPara(res.id);
            aplicarEstado(res.el, registro);
            trackear(res.el);
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
        if (win.__disenoKeydownHandler) { win.removeEventListener('keydown', win.__disenoKeydownHandler); }

        win.__disenoScrollHandler = sync;
        win.__disenoResizeHandler = sync;
        win.__disenoKeydownHandler = function(e) {
            if (e.altKey && (e.key === 'd' || e.key === 'D') && disenoActivo()) {
                win.__disenoState.panelColapsado = !win.__disenoState.panelColapsado;
                panel.dataset.builtForKey = '';
                sync();
            }
        };
        win.addEventListener('scroll', win.__disenoScrollHandler, true);
        win.addEventListener('resize', win.__disenoResizeHandler);
        win.addEventListener('keydown', win.__disenoKeydownHandler);

        win.__disenoPollInterval = win.setInterval(sync, 150);
        sync();

    })();
    </script>
    """
