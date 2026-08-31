"""inyecciones._diseno_js - el JS del modo de diseno visual.

Blob de 794 lineas que estaba embebido como un unico inyectar_html
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

        // El overlay tiene pointer-events:none a proposito (regla de mas
        // abajo: hay que poder ver/medir lo de ABAJO), asi que un click
        // izquierdo normal siempre sigue de largo hasta el widget real. En
        // un boton del rail eso dispara on_click -> session_state["_nav_reporte"]
        // -> Streamlit cambia de reporte a mitad de una sesion de diseno:
        // las keys que se estaban ajustando ya no existen en el DOM nuevo.
        // Pedido explicito 2026-08-23: "inactivar el clickeo" mientras se
        // disena. Contenedores en esta lista quedan exceptuados (son la UI
        // del propio diseno/inspector/barra, no la app).
        function esUIPropiaDeDiseno(nodo) {
            var ids = ['el-diseno-overlay', 'el-diseno-panel', 'herr-barra',
                       'herr-panel', 'el-inspector-tip', 'el-inspector-badge'];
            for (var i = 0; i < ids.length; i++) {
                var c = doc.getElementById(ids[i]);
                if (c && c.contains(nodo)) return true;
            }
            return false;
        }

        // Cartelito efimero que explica un click comido por el bloqueador.
        // Vive en el overlay propio (no en el arbol de Streamlit) para que un
        // rerun no lo borre a mitad de la animacion, y se auto-borra a los
        // 1.6s. `pointer-events:none` para que no se coma el click siguiente.
        function avisarBloqueo(x, y) {
            var prev = doc.getElementById('el-diseno-aviso-bloqueo');
            if (prev) { prev.remove(); }
            var av = doc.createElement('div');
            av.id = 'el-diseno-aviso-bloqueo';
            av.textContent = '🎨 Modo diseño: navegación bloqueada · apagalo en la barra de abajo';
            av.style.cssText = [
                'position:fixed', 'z-index:2147483647', 'pointer-events:none',
                'left:' + Math.min(x + 14, win.innerWidth - 340) + 'px',
                'top:' + Math.max(y - 40, 8) + 'px',
                'max-width:330px', 'padding:7px 11px', 'border-radius:8px',
                'background:rgba(28,26,48,.94)', 'color:#fff',
                'font:500 11.5px/1.35 -apple-system,Segoe UI,sans-serif',
                'box-shadow:0 4px 14px rgba(15,15,30,.28)',
                'transition:opacity .25s', 'opacity:1',
            ].join(';');
            doc.body.appendChild(av);
            win.setTimeout(function () { av.style.opacity = '0'; }, 1200);
            win.setTimeout(function () { av.remove(); }, 1600);
        }

        if (!win.__disenoState) {
            win.__disenoState = { porKey: {}, panelColapsado: false };
        }
        if (win.__disenoState.panelColapsado === undefined) {
            win.__disenoState.panelColapsado = false;
        }
        // Empujar el lienzo (regla #256): el panel es `fixed` a la derecha,
        // asi que TAPA los ~230px de esa orilla — justo donde caen la
        // columna derecha de las tarjetas y el borde de las tablas. Off por
        // defecto a proposito: encoger el lienzo cambia el ancho util y
        // puede disparar las @media de _99_movil, o sea que lo que se ve
        // deja de ser fiel. Es el usuario el que elige "no me tapes" sobre
        // "mostrame el ancho real".
        if (win.__disenoState.empujarLienzo === undefined) {
            win.__disenoState.empujarLienzo = false;
        }
        if (!win.__disenoState.mocks) { win.__disenoState.mocks = []; }
        if (win.__disenoState.mockN === undefined) { win.__disenoState.mockN = 0; }
        if (!win.__disenoState.mockPos) { win.__disenoState.mockPos = 'despues'; }
        // Uniones (regla #194): pares de tarjetas VECINAS que se ven como
        // una sola. Se guardan las dos keys + el eje + el hueco medido al
        // unirlas, nunca los nodos — un rerun los recrea, igual que los
        // mocks y el sub-pin.
        if (!win.__disenoState.uniones) { win.__disenoState.uniones = []; }
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
                    filaAlto: { original: null, actual: null },
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

        // ── Resolver una key al elemento REAL, nunca a una copia ─────────
        // Una copia (regla #258) conserva las clases `st-key-*` del original
        // —es lo que la hace verse igual, porque el CSS del proyecto matchea
        // por esas clases— asi que a partir de ahi hay DOS nodos con la
        // misma key y `querySelector` devuelve el primero del DOM. Insertar
        // la copia "Antes" bastaba para que el pin, el contorno y el ancla
        // de los mocks pasaran a apuntar al clon en vez de al widget que se
        // esta editando. Todos los nodos de una copia (la raiz y su
        // descendencia) llevan `data-diseno-mock`, asi que un solo `:not()`
        // los saca a todos.
        var SIN_COPIAS = ':not([data-diseno-mock])';
        function porKeyReal(key) {
            return doc.querySelector('.st-key-' + key + SIN_COPIAS);
        }

        // Hijos del widget pineado que tienen clase propia pero NO key: los
        // unicos que el modo diseno no podia tocar. Se excluye lo que viva
        // dentro de OTRO `st-key-` mas adentro (eso es otro widget: se pinea
        // por su key, no bajando desde aca) y lo que sea SVG (un Plotly sin
        // key propia inunda la lista con `main-svg`/`trace`/`point`).
        function hijosConClasePropia(key) {
            var base = porKeyReal(key);
            if (!base) return [];
            var out = [], vistas = {};
            var cand = base.querySelectorAll('[class]');
            for (var i = 0; i < cand.length && out.length < 12; i++) {
                var n = cand[i];
                if (n.ownerSVGElement || (n.tagName || '').toLowerCase() === 'svg') continue;
                // Internos de Plotly (.js-plotly-plot, .plot-container,
                // .svg-container, .gl-container, .user-select-none...):
                // son de la libreria, no del autor, y `esClaseDeAutor` no
                // los agarra porque no llevan prefijo st-/ag-/css-. Sin
                // este corte, el arbol de un grafico abre con seis hojas
                // azules que nadie va a estilar nunca y empujan a las
                // utiles fuera del tope de 12. El asa del autor para un
                // grafico es su contenedor con key, no el DOM de Plotly.
                if (n.closest && n.closest('.js-plotly-plot')) continue;
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

        // ── Hojas de TEXTO: Plotly (SVG) y AgGrid (iframe) ───────────────
        // Pedido 2026-08-23: "editar los textos dentro de las tablas y
        // graficos". Son los dos huecos que `hijosConClasePropia` NO puede
        // cubrir, y por motivos distintos:
        //  · Plotly dibuja <text> dentro del SVG, y esa funcion saltea SVG
        //    a proposito: sus clases (.xtick, .gtitle) se repiten en cada
        //    nodo, asi que no sirven como selector unico.
        //  · AgGrid vive en un IFRAME, y `doc.querySelectorAll` del padre
        //    no entra ahi nunca. Es same-origin (medido en vivo), asi que
        //    `contentDocument` SI abre — pero hay que pedirlo explicito.
        // Por eso se direccionan por (tipo, indice, texto) y no por clase.
        // Ver arquitectura.md #182.
        function nodosDeTexto(key, tipo) {
            var base = porKeyReal(key);
            if (!base) return [];
            var out = [], i;
            if (tipo === 'svgtext') {
                var ts = base.querySelectorAll('.js-plotly-plot text');
                for (i = 0; i < ts.length; i++) {
                    if ((ts[i].textContent || '').trim()) out.push(ts[i]);
                }
                return out;
            }
            var ifs = base.querySelectorAll('iframe');
            for (var f = 0; f < ifs.length; f++) {
                var d = null;
                try { d = ifs[f].contentDocument; } catch (e) { continue; }
                if (!d) continue;
                var cs = d.querySelectorAll('.ag-header-cell-text, .ag-cell');
                for (i = 0; i < cs.length; i++) {
                    if ((cs[i].textContent || '').trim()) out.push(cs[i]);
                }
            }
            return out;
        }

        // Tope de 10 por familia: un grid con 200 celdas haria un arbol
        // inusable, y para "ver como se veria" alcanza con las primeras.
        function hojasDeTexto(key) {
            var out = [];
            ['svgtext', 'agtext'].forEach(function (tipo) {
                var ns = nodosDeTexto(key, tipo);
                for (var i = 0; i < ns.length && i < 10; i++) {
                    out.push({ tipo: tipo, idx: i,
                               txt: (ns[i].textContent || '').trim() });
                }
            });
            return out;
        }

        // Por TEXTO antes que por indice: Plotly reordena sus <text> al
        // redibujar (cambiar de granularidad reescribe el eje entero), y
        // ahi el indice guardado apunta a otro rotulo. `txtVivo` es el
        // override aplicado — sin el, cambiar el texto rompia el ancla.
        function resolverNodoTexto(key, sub) {
            var ns = nodosDeTexto(key, sub.tipo);
            if (!ns.length) return null;
            for (var i = 0; i < ns.length; i++) {
                var t = (ns[i].textContent || '').trim();
                if (t === sub.txt || (sub.txtVivo && t === sub.txtVivo)) return ns[i];
            }
            return ns[sub.idx] || null;
        }

        function elementoPineado() {
            // win.__inspectorUltimo.elemento es el nodo del momento del pin;
            // no confiar en esa referencia — re-resolver por key siempre.
            if (!win.__inspectorPinned || !win.__inspectorUltimo) return null;
            var key = win.__inspectorUltimo.key;
            if (!key) return null;
            var base = porKeyReal(key);
            var sub = win.__disenoState.sub;
            // El sub muere con su key: si el pin salto a otro widget, lo que
            // haya guardado ya no aplica (y su clase podria existir alla
            // adentro y pinear un hijo distinto sin aviso).
            if (sub && sub.key !== key) { win.__disenoState.sub = null; sub = null; }
            if (!sub) return { key: key, sub: '', id: key, el: base };
            // Hoja de texto (Plotly/AgGrid): no tiene clase que sirva de
            // ancla, se resuelve por (tipo, idx, texto). El id lleva el
            // texto para que dos rotulos del MISMO grafico no compartan
            // registro de cambios.
            if (sub.tipo) {
                return { key: key, sub: '', subTexto: sub,
                         id: key + ' «' + sub.txt + '»',
                         el: base ? resolverNodoTexto(key, sub) : null };
            }
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
                                   subTexto: r.subTexto,
                                   registro: registroPara(r.id) } : null;
        }

        function bajarASub(clase) {
            var r = elementoPineado();
            if (!r) return;
            win.__disenoState.sub = { key: r.key, clase: clase };
            panel.dataset.builtForKey = '';   // fuerza reconstruir con el sub
            sync();
        }

        // Que sub-pin le corresponde al nodo que el usuario senalo de verdad.
        // Devuelve null si apunto al contenedor pelado (ahi el pin es la
        // tarjeta, como siempre).
        function subDesdeNodo(key, nodo) {
            var base = porKeyReal(key);
            if (!base || !nodo || nodo === base) return null;
            var tipos = ['svgtext', 'agtext'], t, i;
            for (t = 0; t < tipos.length; t++) {
                var ns = nodosDeTexto(key, tipos[t]);
                for (i = 0; i < ns.length; i++) {
                    if (ns[i] === nodo || ns[i].contains(nodo)) {
                        return { key: key, tipo: tipos[t], idx: i,
                                 txt: (ns[i].textContent || '').trim() };
                    }
                }
            }
            // Sin coincidencia de texto: subir hasta el primer hijo con
            // clase de autor (el camino viejo, el de `.cp-rank-tit`).
            var cur = nodo;
            while (cur && cur !== base) {
                var cls = cur.classList || [];
                for (i = 0; i < cls.length; i++) {
                    if (esClaseDeAutor(cls[i])) return { key: key, clase: cls[i] };
                }
                cur = cur.parentElement;
            }
            return null;
        }

        // El sub-pin se RECALCULA cada vez que el inspector fija un nodo
        // distinto. Antes solo se soltaba al cambiar de KEY
        // (`sub.key !== key` en elementoPineado), asi que fijar otra cosa
        // DENTRO de la misma tarjeta dejaba vivo el sub anterior.
        // Reportado 2026-08-23 con captura: con «Aug 2026» (un texto de
        // Plotly) ya elegido, hacer clic derecho sobre el titulo "Ranking
        // de productos" seguia mostrando el texto de Plotly — misma key,
        // sub viejo. Se noto recien ahora porque las hojas de texto
        // (regla #182) multiplicaron por diez los subs posibles por
        // tarjeta. Ver arquitectura.md #184.
        // Clic derecho DENTRO de un iframe (la grilla de AgGrid).
        //
        // Reportado 2026-08-23: "cuando selecciono las tablas no me permite
        // disenarlo". Y era cierto para el gesto natural: el listener de
        // `contextmenu` del inspector vive en el documento PADRE, y un
        // clic sobre una celda ocurre dentro del documento del iframe, que
        // no propaga al padre. Medido: clic derecho sobre una celda dejaba
        // `__inspectorPinned` en false y el panel en estado de espera.
        // El camino indirecto (fijar la tarjeta -> hoja ▦ del arbol) ya
        // andaba desde la regla #182, pero nadie lo adivina.
        // Se engancha un listener PROPIO en cada iframe same-origin, que
        // traduce el nodo de adentro a un sub-pin y pinea el contenedor
        // con key de afuera. Ver arquitectura.md #185.
        function engancharIframes() {
            var ifs = doc.querySelectorAll('iframe');
            for (var i = 0; i < ifs.length; i++) {
                var fdoc = null;
                try { fdoc = ifs[i].contentDocument; } catch (e) { continue; }
                if (!fdoc || !fdoc.body || fdoc.__disenoEnganchado) continue;
                fdoc.__disenoEnganchado = true;
                (function (frame, d2) {
                    d2.addEventListener('contextmenu', function (e) {
                        if (!disenoActivo()) return;
                        e.preventDefault();
                        var cont = frame.closest('[class*="st-key-"]');
                        if (!cont) return;
                        var m = /st-key-([A-Za-z0-9_-]+)/.exec(
                            (cont.className || '').toString());
                        if (!m) return;
                        var key = m[1];
                        var ns = nodosDeTexto(key, 'agtext'), idx = -1;
                        for (var j = 0; j < ns.length; j++) {
                            if (ns[j] === e.target || ns[j].contains(e.target)) {
                                idx = j; break;
                            }
                        }
                        // El sub va por una bandera y no directo: mas abajo
                        // `saltarADiseno` limpia el sub y re-pinea, asi que
                        // escribirlo aca se perderia. La consume
                        // sincronizarSubConElPin() en el sync() siguiente.
                        win.__disenoSubForzado = (idx >= 0)
                            ? { key: key, tipo: 'agtext', idx: idx,
                                txt: (ns[idx].textContent || '').trim() }
                            : null;
                        saltarADiseno(key);
                        // `saltarADiseno` solo pinea (llama a
                        // __inspectorTogglePin directo, no pasa por el
                        // contextmenu handler del inspector) — clic derecho
                        // DENTRO de la grilla se quedaba sin el "ademas
                        // copia" que el gesto tiene en cualquier otro lado
                        // de la app. Mismo "un solo gesto" que arquitectura.md
                        // #185 dejo pendiente.
                        win.__inspectorEjecutarCopia && win.__inspectorEjecutarCopia();
                    }, true);
                })(ifs[i], fdoc);
            }
        }

        function sincronizarSubConElPin() {
            var u = win.__inspectorUltimo;
            // OJO: `u.elemento` ya es el CONTENEDOR con key que resolvio el
            // inspector — usarlo aca daria siempre la tarjeta y nunca un
            // sub. El nodo que el usuario senalo de verdad es
            // `elementoOriginal`, y es el unico que sabe si apunto al
            // titulo o a un tick del grafico.
            var nodo = u ? (u.elementoOriginal || u.elemento) : null;
            if (!win.__inspectorPinned || !u || !nodo || !u.key) {
                // Soltar el pin habilita volver a fijar EL MISMO nodo y que
                // se recalcule igual (si no, el guard de abajo lo saltea).
                win.__disenoUltimoNodoPin = null;
                return;
            }
            // Sub pedido desde adentro de un iframe: gana, y se consume una
            // sola vez. Va ANTES del guard por nodo porque el nodo pineado
            // es el CONTENEDOR (el iframe no tiene representacion propia en
            // el arbol del padre), asi que el guard lo saltearia.
            if (win.__disenoSubForzado) {
                win.__disenoUltimoNodoPin = nodo;
                win.__disenoState.sub = win.__disenoSubForzado;
                win.__disenoSubForzado = null;
                panel.dataset.builtForKey = '';
                return;
            }
            if (win.__disenoUltimoNodoPin === nodo) return;
            win.__disenoUltimoNodoPin = nodo;
            win.__disenoState.sub = subDesdeNodo(u.key, nodo);
            panel.dataset.builtForKey = '';   // reconstruir con el sub nuevo
        }

        function bajarASubTexto(hoja) {
            var r = elementoPineado();
            if (!r) return;
            win.__disenoState.sub = { key: r.key, tipo: hoja.tipo,
                                      idx: hoja.idx, txt: hoja.txt };
            panel.dataset.builtForKey = '';
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
            var el = porKeyReal(key);
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
                          ['barra', 'Barra'], ['espacio', 'Espacio'],
                          ['copia', 'Copia']];

        // Marca la copia ENTERA (raiz + descendencia) para que porKeyReal()
        // la ignore: las keys de los hijos tambien se duplican al clonar una
        // tarjeta, no solo la de la raiz. Y borra los `id`, que en HTML son
        // unicos — un id repetido rompe getElementById para el original.
        function marcarCopia(raiz) {
            raiz.removeAttribute('id');
            var todos = raiz.querySelectorAll('*');
            for (var i = 0; i < todos.length; i++) {
                todos[i].removeAttribute('id');
                todos[i].setAttribute('data-diseno-mock', 'hijo');
            }
        }

        function nodoMock(m, origen) {
            if (m.tipo === 'copia') {
                if (!origen) return null;
                // Clon PROFUNDO y con las clases intactas: el CSS del
                // proyecto matchea por `.st-key-*`, asi que quitarlas
                // dejaria una copia sin estilo — un esqueleto, no una
                // maqueta. Ver regla #258 para el trade-off.
                var cp = origen.cloneNode(true);
                marcarCopia(cp);
                cp.className = (cp.className || '') + ' st-key-' + m.key;
                cp.setAttribute('data-diseno-mock', m.tipo);
                // Muerto a proposito: es HTML copiado, sin sesion de
                // Streamlit detras. Dejarlo clickeable invitaria a probar
                // botones que no hacen nada.
                cp.style.pointerEvents = 'none';
                return cp;
            }
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
            var ancla = porKeyReal(m.anclaKey);
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
            // El origen de una copia es el ancla REAL, no la encadenada:
            // anclaEfectiva() puede devolver un mock anterior cuando varios
            // se insertan "despues" del mismo sitio, y clonar una copia de
            // una copia multiplicaria el error.
            var origen = null;
            if (m.tipo === 'copia') {
                origen = porKeyReal(m.anclaKey);
                if (origen && m.anclaSub) origen = origen.querySelector('.' + m.anclaSub);
                if (!origen) return false;
            }
            var el = nodoMock(m, origen);
            if (!el) return false;
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
                // "Dentro" de si mismo no significa nada para una copia
                // (deja un clon del padre colgando adentro del padre): se
                // degrada a "Despues", que es lo que se pide al duplicar.
                posicion: (tipo === 'copia' && win.__disenoState.mockPos === 'dentro')
                    ? 'despues' : win.__disenoState.mockPos,
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

        function esCopia(key) {
            var ms = win.__disenoState.mocks;
            for (var i = 0; i < ms.length; i++) {
                if (ms[i].key === key) return ms[i].tipo === 'copia';
            }
            return false;
        }

        // ---- unificar: dos tarjetas vecinas vistas como una sola --------
        // "Como se veria si estas dos fueran UNA tarjeta": se cierra el
        // hueco que las separa y se sacan las esquinas del lado que se
        // tocan. NO se mueve un solo nodo — sacar un subarbol de Streamlit
        // de su padre y meterlo en otro revienta a React en el rerun
        // siguiente (guarda la referencia al padre VIEJO para su
        // removeChild). Todo sale por `registro.cambios` de las DOS keys,
        // asi que revertir, "Ver original" y "Copiar CSS" salen gratis.
        //
        // Lo que esto NO es: unificarlas de verdad (un solo st.container
        // con las dos cosas adentro) es un cambio de Python en graficos/.
        // Esto entrega el look y el CSS del pegado, que es la mitad
        // visual; el panel y el bloque copiado lo dicen explicito.
        var TOL_UNION = 6;     // px de desalineacion tolerada en el eje transversal
        // px de hueco: mas separadas que esto ya no son vecinas. Medido en
        // el drill de Proveedor: entre dos tarjetas de verdad hay 16px (el
        // gap de st.columns, y el margin-top de _80_cards entre apiladas).
        // Con 80 se colaban dos falsos vecinos que estan cerca pero no al
        // lado — el item del rail a 51px de la tarjeta y la franja de
        // arriba a 53px —, y la lista de "pegar con" salia con mas ruido
        // que candidatas.
        var HUECO_MAX = 40;
        var PROPS_UNION = {
            h: { primero: ['border-top-right-radius', 'border-bottom-right-radius'],
                 segundo: ['border-top-left-radius', 'border-bottom-left-radius'],
                 nombre: 'horizontal' },
            v: { primero: ['border-bottom-left-radius', 'border-bottom-right-radius'],
                 segundo: ['border-top-left-radius', 'border-top-right-radius'],
                 nombre: 'vertical' }
        };
        var FLECHA_LADO = { izquierda: '\u25c0', derecha: '\u25b6',
                            arriba: '\u25b2', abajo: '\u25bc' };

        // Estricta a proposito, al reves que keyDeNodo() (que cae al
        // testid/tag): sin key no hay selector que pegar en estilos/, asi
        // que esa vecina directamente no se ofrece.
        function keyPropiaDe(nodo) {
            var cls = (nodo.className && nodo.className.toString
                       ? nodo.className.toString() : '').split(' ');
            for (var i = 0; i < cls.length; i++) {
                if (cls[i].indexOf('st-key-') === 0) return cls[i].slice(7);
            }
            return null;
        }

        // "Pinta" = tiene fondo opaco, sombra o borde propio. Es lo que
        // separa una TARJETA de un wrapper de layout con key, que miden lo
        // mismo y son indistinguibles por geometria (medido en vivo:
        // `docs_row` y `compras_prov_card_docs` dan los DOS 841x547).
        // Importa porque sacarle una esquina o el hueco a una caja
        // transparente no cambia un pixel en pantalla.
        function pintaAlgo(n) {
            var cs = win.getComputedStyle(n);
            var bg = cs.backgroundColor || '';
            var opaco = bg && bg !== 'transparent' && bg.indexOf('rgba(0, 0, 0, 0)') !== 0;
            return (opaco || (cs.boxShadow && cs.boxShadow !== 'none')
                    || parseFloat(cs.borderTopWidth) > 0) ? 1 : 0;
        }

        function vecinasUnibles(el) {
            var ra = el.getBoundingClientRect();
            if (!ra.width || !ra.height) return [];
            var cands = [], todos = doc.querySelectorAll('div[class*="st-key-"]');
            for (var i = 0; i < todos.length; i++) {
                var n = todos[i];
                if (n === el || n.contains(el) || el.contains(n)) continue;
                var k = keyPropiaDe(n);
                if (!k || esMock(k)) continue;
                var r = n.getBoundingClientRect();
                if (r.width < 40 || r.height < 40) continue;
                var lado = null, eje = 'h', hueco = 0;
                // Alineadas por el techo = misma fila (columnas hermanas);
                // por el borde izquierdo = misma columna, una sobre otra.
                // El horizontal se prueba PRIMERO: dos tarjetas de la misma
                // fila pueden compartir tambien el `left` si la de al lado
                // arranca en el mismo x por casualidad de un ancho raro.
                if (Math.abs(r.top - ra.top) <= TOL_UNION) {
                    if (r.left - ra.right >= -2 && r.left - ra.right <= HUECO_MAX) {
                        lado = 'derecha'; hueco = r.left - ra.right;
                    } else if (ra.left - r.right >= -2 && ra.left - r.right <= HUECO_MAX) {
                        lado = 'izquierda'; hueco = ra.left - r.right;
                    }
                }
                if (!lado && Math.abs(r.left - ra.left) <= TOL_UNION) {
                    eje = 'v';
                    if (r.top - ra.bottom >= -2 && r.top - ra.bottom <= HUECO_MAX) {
                        lado = 'abajo'; hueco = r.top - ra.bottom;
                    } else if (ra.top - r.bottom >= -2 && ra.top - r.bottom <= HUECO_MAX) {
                        lado = 'arriba'; hueco = ra.top - r.bottom;
                    }
                }
                if (!lado) continue;
                cands.push({ key: k, lado: lado, eje: eje,
                             hueco: Math.max(0, Math.round(hueco)),
                             area: r.width * r.height, pinta: pintaAlgo(n),
                             desnivel: Math.round(eje === 'h' ? (r.height - ra.height)
                                                              : (r.width - ra.width)) });
            }
            // Una vecina trae ENCIMADAS todas sus cajas con key: la tarjeta,
            // sus wrappers de layout y los widgets de adentro que arranquen
            // en el mismo borde. Por cada lado se ofrece UNA: primero la que
            // pinta (la tarjeta), y entre iguales la mas grande — la de
            // afuera, con el fondo y las esquinas que hay que sacar. Con una
            // de adentro, la costura quedaria a medio hacer.
            var porLado = {};
            cands.forEach(function(c) {
                var m = porLado[c.lado];
                if (!m || c.pinta > m.pinta || (c.pinta === m.pinta && c.area > m.area)) {
                    porLado[c.lado] = c;
                }
            });
            var out = [];
            ['izquierda', 'derecha', 'arriba', 'abajo'].forEach(function(l) {
                if (porLado[l]) out.push(porLado[l]);
            });
            return out;
        }

        function unionesDe(key) {
            return win.__disenoState.uniones.filter(function(u) {
                return u.a === key || u.b === key;
            });
        }

        // `a` es SIEMPRE la primera en el orden visual (izquierda o arriba).
        function aplicarUnion(u) {
            var elA = porKeyReal(u.a);
            var elB = porKeyReal(u.b);
            if (!elA || !elB) return false;   // otro reporte: queda dormida
            var mapa = PROPS_UNION[u.eje];
            var regA = registroPara(u.a), regB = registroPara(u.b);
            mapa.primero.forEach(function(p) { regA.cambios[p] = '0'; });
            mapa.segundo.forEach(function(p) { regB.cambios[p] = '0'; });
            // El hueco lo pone el `gap` del bloque de Streamlit, que NO
            // tiene key: no hay selector estable que pegar en estilos/, asi
            // que se cierra desde una de las dos tarjetas. Cual, depende del
            // eje — y la diferencia se ve:
            //
            // AL LADO: crece la PRIMERA hacia la derecha. Correr la segunda
            // hacia la izquierda tambien cierra la costura, pero le mete el
            // borde derecho 16px adentro y la union queda mas angosta que la
            // fila (medido: 349..1174 contra los 349..1190 de la tarjeta de
            // abajo, un escaloncito justo donde uno esta mirando si alinea).
            // El `width` va con calc porque la tarjeta tiene ancho definido
            // (flex item de la columna): sin el, el margen negativo la
            // corre en vez de estirarla.
            //
            // APILADAS: se corre la SEGUNDA hacia arriba, y ahi si es lo
            // correcto — una tarjeta unica de verdad tambien subiria todo lo
            // que viene despues.
            if (u.hueco > 0) {
                if (u.eje === 'h') {
                    regA.cambios.width = 'calc(100% + ' + u.hueco + 'px)';
                    // `max-width: none` no es decorativo (arquitectura.md
                    // #47): los contenedores de Streamlit traen
                    // max-width:100% y sin sacarlo el calc queda clampeado
                    // al ancho del padre — medido, la tarjeta seguia en
                    // 509.5px con el width nuevo puesto y con !important.
                    regA.cambios['max-width'] = 'none';
                    regA.cambios['margin-right'] = '-' + u.hueco + 'px';
                } else {
                    regB.cambios['margin-top'] = '-' + u.hueco + 'px';
                }
            }
            // Apiladas, la sombra de la de ARRIBA cae justo sobre la
            // costura (offset +1px hacia abajo) y se ve como una linea que
            // parte la tarjeta al medio. Al lado no molesta: la sombra de
            // estas tarjetas no se proyecta a los costados.
            if (u.eje === 'v') regA.cambios['box-shadow'] = 'none';
            aplicarEstado(elA, regA);
            aplicarEstado(elB, regB);
            return true;
        }

        // Espejo exacto de aplicarUnion(): que props escribio en cada key.
        // Si una se agrega alla y no aca, "Separar" la deja pegada por esa
        // sola propiedad y no hay forma de sacarla desde el panel.
        function propsDeUnion(u, key) {
            var mapa = PROPS_UNION[u.eje];
            var esPrimera = (u.a === key);
            var props = esPrimera ? mapa.primero.slice() : mapa.segundo.slice();
            if (u.hueco > 0) {
                if (u.eje === 'h' && esPrimera) { props.push('width', 'max-width', 'margin-right'); }
                if (u.eje === 'v' && !esPrimera) { props.push('margin-top'); }
            }
            if (u.eje === 'v' && esPrimera) props.push('box-shadow');
            return props;
        }

        function separarUnion(u) {
            win.__disenoState.uniones = win.__disenoState.uniones.filter(function(x) {
                return x !== u;
            });
            [u.a, u.b].forEach(function(k) {
                var el = porKeyReal(k);
                var reg = registroPara(k);
                propsDeUnion(u, k).forEach(function(p) {
                    delete reg.cambios[p];
                    if (!el) return;
                    el.style.removeProperty(p);
                    // El tick reaplica por destinosDeEstilo(), asi que la
                    // limpieza tiene que barrer los MISMOS nodos o la
                    // propiedad sobrevive donde nadie la esta mirando.
                    destinosDeEstilo(el).forEach(function(d) { d.style.removeProperty(p); });
                });
                if (el) aplicarEstado(el, reg);
            });
        }

        function unir(keyPin, cand) {
            var primeroEsPin = (cand.lado === 'derecha' || cand.lado === 'abajo');
            var u = { a: primeroEsPin ? keyPin : cand.key,
                      b: primeroEsPin ? cand.key : keyPin,
                      eje: cand.eje, hueco: cand.hueco };
            var ya = win.__disenoState.uniones.some(function(x) {
                return x.a === u.a && x.b === u.b;
            });
            if (!ya) { win.__disenoState.uniones.push(u); aplicarUnion(u); }
            panel.dataset.builtForKey = '';   // cambio la lista de vecinas
            sync();
        }

        // La lista de "pegar con la vecina" se repinta SOLA cada ~1 segundo,
        // aparte del resto del panel: sale de medir rects, y al fijar una
        // tarjeta la de al lado puede no estar todavia donde va a quedar
        // (la de documentos monta un iframe de AgGrid y se acomoda despues).
        // Medido: fijando el ranking del drill de Proveedor, el "▼
        // compras_prov_card_docs" aparecia o no segun cuando se pineaba, y
        // el panel entero solo se reconstruye si cambia la key — la lista
        // quedaba congelada en lo que hubiera en pantalla ese instante.
        // Repintar SOLO esta caja evita el otro extremo: reconstruir el
        // panel en cada tick le sacaria el foco a un slider a mitad de un
        // arrastre. La firma corta el repintado cuando no cambio nada.
        function pintarVecinas() {
            var caja = panel.__cajaVecinas;
            if (!caja || !caja.isConnected) return;
            var key = panel.__vecinasDe;
            // Se busca desde la caja de la KEY, no desde el elemento
            // pineado: con sub-pin ese es un hijo (el titulo de la tarjeta)
            // y sus vecinos son los otros hijos, no las tarjetas de al lado.
            // Una union es entre keys — es lo unico que se puede escribir
            // despues en estilos/.
            var elUnion = porKeyReal(key);
            var yaUnidas = {}, hayUnion = false;
            unionesDe(key).forEach(function(u) {
                yaUnidas[(u.a === key) ? u.b : u.a] = 1;
                hayUnion = true;
            });
            var vecinas = elUnion ? vecinasUnibles(elUnion).filter(function(c) {
                return !yaUnidas[c.key];
            }) : [];
            var firma = vecinas.map(function(c) {
                return c.lado + ':' + c.key + ':' + c.hueco;
            }).join('|') + (hayUnion ? '|u' : '');
            if (firma === panel.__vecinasFirma) return;
            panel.__vecinasFirma = firma;
            caja.innerHTML = '';
            if (!vecinas.length) {
                if (hayUnion) return;
                var sinVec = doc.createElement('div');
                sinVec.style.cssText = 'font-size:10px;line-height:1.45;color:#8b8b95;margin-top:6px';
                sinVec.textContent = 'Ninguna caja con key arranca en el mismo borde a menos de '
                    + HUECO_MAX + 'px. Fijá la tarjeta entera (la que tiene el fondo),'
                    + ' no un widget de adentro.';
                caja.appendChild(sinVec);
                return;
            }
            var wrapVec = doc.createElement('div');
            wrapVec.style.cssText = 'display:flex;flex-direction:column;gap:4px;margin-top:6px';
            vecinas.forEach(function(c) {
                var b = doc.createElement('button');
                b.textContent = FLECHA_LADO[c.lado] + ' ' + c.key;
                b.title = 'Vecina de ' + c.lado + ' - hueco ' + c.hueco + 'px'
                    + (Math.abs(c.desnivel) > 2
                        ? (', y ' + Math.abs(c.desnivel) + 'px de desnivel: la costura va a quedar despareja')
                        : '');
                b.style.cssText = 'width:100%;text-align:left;background:#1c1c24;color:#e4e4e8;border:1px solid #34343f;border-radius:4px;padding:6px 7px;font:10px "Courier New",monospace;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
                b.addEventListener('click', function() {
                    var ctx = elementoActivo();
                    if (ctx) unir(ctx.key, c);
                });
                wrapVec.appendChild(b);
            });
            caja.appendChild(filaControl('Pegar con la vecina', wrapVec, spanValor('')));
        }

        // Idempotente y barata: es la que hace que la union sobreviva un
        // rerun (Streamlit recrea los nodos y se lleva los inline con
        // ellos) sin depender de cual de las dos tarjetas este pineada —
        // el aplicarEstado() del tick solo toca la pineada.
        function reaplicarUniones() {
            var us = win.__disenoState.uniones;
            for (var i = 0; i < us.length; i++) { aplicarUnion(us[i]); }
        }

        // ---- overlay (outline + manijas) y panel lateral ----
        var overlay = doc.getElementById('el-diseno-overlay');
        if (!overlay) {
            overlay = doc.createElement('div');
            overlay.id = 'el-diseno-overlay';
            overlay.style.cssText = [
                'position:fixed',
                // El MAXIMO, y un escalon por encima del tooltip del
                // inspector (2147483646): las manijas tienen que poder
                // agarrarse aunque el elemento se haya movido hasta debajo
                // del tooltip fijado. Regla #257.
                'z-index:2147483647',
                'pointer-events:none',
                'border:2px solid #6c5ce7',
                'border-radius:4px',
                'box-sizing:border-box',
                'display:none'
            ].join(';');
            doc.body.appendChild(overlay);
        }

        // La reserva se hace con una <style> propia y no tocando
        // .stApp.style: Streamlit recrea/reescribe sus nodos en cada rerun y
        // se llevaria el inline puesto a mano. Una regla en el <head>
        // sobrevive y se apaga cambiando una sola variable.
        var ANCHO_PANEL = 230;
        function aplicarReserva(activa) {
            var st = doc.getElementById('el-diseno-reserva');
            if (!st) {
                st = doc.createElement('style');
                st.id = 'el-diseno-reserva';
                doc.head.appendChild(st);
            }
            st.textContent = activa
                ? ('.stApp { width: calc(100% - ' + ANCHO_PANEL + 'px) !important; }')
                : '';
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
            var ox = Math.round(r.left - s), oy = Math.round(r.top - s);
            var ow = Math.round(r.width + s * 2), oh = Math.round(r.height + s * 2);
            overlay.style.left = ox + 'px';
            overlay.style.top = oy + 'px';
            overlay.style.width = ow + 'px';
            overlay.style.height = oh + 'px';
            clampManijas(ox, oy, ow, oh);
        }

        // Las manijas cuelgan del contorno con offsets NEGATIVOS (viven por
        // FUERA del elemento, para no taparlo). Si el elemento toca un borde
        // de la ventana esa posicion cae fuera del viewport y la manija se
        // vuelve INALCANZABLE: reportado con `nav_rail`, que vive en top:0 —
        // la perilla de mover quedaba en y=-17 y no habia forma de agarrarla
        // (regla #168).
        //
        // Cuando no hay sitio afuera, la manija se mete ADENTRO. El clamp se
        // calcula contra el viewport ABSOLUTO y no contra el overlay: con el
        // overlay ya 4px afuera, un simple "poner 2px" seguia dejandola medio
        // fuera de la pantalla.
        function clampManijas(ox, oy, ow, oh) {
            var vw = win.innerWidth, vh = win.innerHeight, M = 2;
            // El PANEL lateral tambien tapa: un elemento ancho (nav_rail mide
            // 1264px) llega por debajo suyo y sus manijas derechas quedan
            // dentro del viewport pero incliqueables. Se trata su borde
            // izquierdo como el limite derecho real, y solo cuando el panel
            // se cruza verticalmente con el elemento — si no, un panel
            // colapsado abajo a la derecha recortaria manijas que se ven bien.
            var pnl = doc.getElementById('el-diseno-panel');
            if (pnl && pnl.style.display !== 'none') {
                var pr = pnl.getBoundingClientRect();
                if (pr.width > 0 && pr.bottom > oy && pr.top < oy + oh) {
                    vw = Math.min(vw, Math.round(pr.left));
                }
            }
            function pos(id, prop, deseado, calcularMin) {
                var h = doc.getElementById(id);
                if (!h) return;
                var min = calcularMin();
                h.style[prop] = (deseado < min ? min : deseado) + 'px';
            }
            // mover: top/left negativos -> su borde sup/izq no puede ser < M
            pos('el-diseno-mover', 'top', -13, function() { return -oy + M; });
            pos('el-diseno-mover', 'left', -13, function() { return -ox + M; });
            // resize: right/bottom negativos -> su borde der/inf no puede
            // pasarse de vw-M / vh-M
            pos('el-diseno-rh-e', 'right', -5, function() { return ox + ow - vw + M; });
            pos('el-diseno-rh-s', 'bottom', -5, function() { return oy + oh - vh + M; });
            pos('el-diseno-rh-se', 'right', -6, function() { return ox + ow - vw + M; });
            pos('el-diseno-rh-se', 'bottom', -6, function() { return oy + oh - vh + M; });
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
        var PROPS_TEXTO = { 'font-size': 1, 'font-weight': 1, 'font-family': 1, 'text-align': 1, 'text-decoration': 1, 'letter-spacing': 1, color: 1 };

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

        // ── Gráficos y tablas: redimensionar el contenedor NO ALCANZA ──────
        // Verificado en vivo (2026-08-23, arquitectura.md regla #175):
        // CLAUDE.md ya avisa que "Plotly no llena su contenedor" — acá se
        // confirmó por qué. Un Plotly (`st.plotly_chart`) trae ancho/alto
        // EXPLICITOS en `fig.layout` (nunca autosize: así vive el contrato
        // de alturas de graficos/alturas.py), así que agrandar el `<div
        // class="js-plotly-plot">` de afuera no mueve un píxel el SVG de
        // adentro — hace falta `Plotly.relayout(gd, {width, height})`, la
        // misma API que usaría cualquier código que lo redimensione a mano.
        // AgGrid (`st_aggrid`) es peor: son TRES cajas con tamaño fijo en
        // cascada, cada una ciega a que la de afuera cambió — el `<iframe>`
        // trae un `height=` HTML (lo pone Streamlit vía postMessage, el
        // protocolo de custom components) y, DENTRO del iframe (mismo
        // origen que la app — se puede entrar sin CORS), el propio React de
        // st_aggrid le clava un `style="width:...px;height:...px"` a su
        // `#gridContainer`. Ninguna de las tres cede con solo agrandar la
        // de afuera. Una vez las tres ceden, ag-grid SÍ se reacomoda solo
        // (su propio ResizeObserver interno) — no hace falta pedirle nada,
        // a diferencia de Plotly.
        function contenidoRedimensionable(elemento) {
            var gd = elemento.classList.contains('js-plotly-plot')
                ? elemento : elemento.querySelector('.js-plotly-plot');
            if (gd) return {tipo: 'plotly', gd: gd};
            var ifr = elemento.querySelector('iframe[title="st_aggrid.AgGrid.agGrid"]');
            if (ifr) return {tipo: 'aggrid', iframe: ifr};
            return null;
        }
        function sincronizarContenidoRedimensionable(elemento, anchoPx, altoPx) {
            if (!anchoPx && !altoPx) return;
            var res = contenidoRedimensionable(elemento);
            if (!res) return;
            if (res.tipo === 'plotly') {
                if (!win.Plotly) return;   // aun no cargo el bundle de Plotly
                var layout = {};
                if (anchoPx) layout.width = anchoPx;
                if (altoPx) layout.height = altoPx;
                try { win.Plotly.relayout(res.gd, layout); } catch (err) {}
                return;
            }
            // aggrid
            if (anchoPx) res.iframe.style.setProperty('width', anchoPx + 'px', 'important');
            if (altoPx) res.iframe.style.setProperty('height', altoPx + 'px', 'important');
            try {
                var doc3 = res.iframe.contentDocument;
                var gridContainer = doc3 && doc3.getElementById('gridContainer');
                if (gridContainer) {
                    if (anchoPx) gridContainer.style.setProperty('width', anchoPx + 'px', 'important');
                    if (altoPx) gridContainer.style.setProperty('height', altoPx + 'px', 'important');
                }
            } catch (err) {}   // cross-origin en algun despliegue raro: degrada a "solo el iframe cambio"
        }

        // ── Un ancestro que RECORTA hace invisible la mitad del resize ───
        // Pedido 2026-08-23: "puedo comprimir el largo o ancho de las
        // tablas? creo que solo me permite acortar". No era la herramienta:
        // arrastrar hacia afuera SI agranda el elemento (medido: pedir 700px
        // sobre una grilla de 473 da 700 en el DOM), pero la tarjeta que la
        // contiene trae `overflow-x: hidden` (estilos/_80_cards.py) y corta
        // 226 de esos px SIN dibujar barra de scroll. Achicar se ve,
        // ensanchar no pasa nada en pantalla — de ahi la lectura de que
        // "solo acorta".
        //
        // Mismo criterio que el bloqueo de clicks: si no va a pasar nada,
        // decirlo mientras pasa, no despues. Devuelve el primer ancestro que
        // este recortando de verdad (no cualquiera que PODRIA recortar).
        var OVERFLOW_RECORTA = { hidden: 1, clip: 1, auto: 1, scroll: 1 };
        function keyDeNodo(nodo) {
            var cls = (nodo.className && nodo.className.toString
                       ? nodo.className.toString() : '').split(' ');
            for (var i = 0; i < cls.length; i++) {
                if (cls[i].indexOf('st-key-') === 0) return cls[i].slice(7);
            }
            return nodo.getAttribute('data-testid') || nodo.tagName.toLowerCase();
        }
        function ancestroQueRecorta(elemento) {
            if (!elemento || !elemento.parentElement) return null;
            var r = elemento.getBoundingClientRect();
            var nodo = elemento.parentElement;
            while (nodo && nodo !== doc.body) {
                var cs = win.getComputedStyle(nodo);
                var cortaX = OVERFLOW_RECORTA[cs.overflowX];
                var cortaY = OVERFLOW_RECORTA[cs.overflowY];
                if (cortaX || cortaY) {
                    var rn = nodo.getBoundingClientRect();
                    // El borde de la CAJA DE CONTENIDO, no el del elemento:
                    // el padding no recorta, pero si corre donde empieza el
                    // corte (18px por lado en las tarjetas de este proyecto).
                    var derecha = rn.right - parseFloat(cs.borderRightWidth || 0)
                                  - parseFloat(cs.paddingRight || 0);
                    var abajo = rn.bottom - parseFloat(cs.borderBottomWidth || 0)
                                - parseFloat(cs.paddingBottom || 0);
                    var exX = cortaX ? Math.round(r.right - derecha) : 0;
                    var exY = cortaY ? Math.round(r.bottom - abajo) : 0;
                    // `auto`/`scroll` no recortan: scrollean. Solo cuentan
                    // como recorte real si ese eje NO tiene por donde
                    // scrollear (su scrollWidth/Height no crecio).
                    if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') {
                        if (nodo.scrollWidth > nodo.clientWidth + 1) exX = 0;
                    }
                    if (cs.overflowY === 'auto' || cs.overflowY === 'scroll') {
                        if (nodo.scrollHeight > nodo.clientHeight + 1) exY = 0;
                    }
                    if (exX > 1 || exY > 1) {
                        return {nodo: nodo, key: keyDeNodo(nodo),
                                x: Math.max(0, exX), y: Math.max(0, exY),
                                overflowX: cs.overflowX, overflowY: cs.overflowY};
                    }
                }
                nodo = nodo.parentElement;
            }
            return null;
        }

        // ── ALTO DE FILA de un AgGrid (preview, como todo aca) ────────
        // Pedido 2026-08-23: "me refiero a achicar las filas". No sale por
        // CSS y no es un descuido: ag-grid posiciona cada fila en ABSOLUTO,
        // con `transform: translateY(indice * alto)` y un `height` inline,
        // los dos calculados en JS. Una regla que baje el `height` deja las
        // filas en su vieja posicion y se pisan.
        //
        // PRIMER INTENTO, DESCARTADO: reescribir a mano lo mismo que escribe
        // ag-grid (alto de cada `.ag-row`, su translateY, y la altura de los
        // contenedores). Se ve bien... hasta que el usuario SCROLLEA, que es
        // exactamente como lo reporto (con captura: filas separadas por
        // huecos enormes). Dos motivos, y el segundo no tiene arreglo por
        // DOM:
        //   1. La guarda de idempotencia miraba la PRIMERA `.ag-row` del
        //      documento. Al reciclar, ag-grid reescribe solo algunas: si la
        //      primera todavia tenia el alto nuestro, el tick se iba sin
        //      corregir las recien recicladas y quedaban conviviendo dos
        //      alturas.
        //   2. Peor: la VIRTUALIZACION sigue calculandose con el rowHeight
        //      de ag-grid. Decide que filas renderizar dividiendo el
        //      scrollTop por SU alto, asi que con el override activo pinta
        //      un rango de filas que no corresponde a la banda visible y
        //      deja el resto en blanco. Ningun parche de DOM lo arregla:
        //      la cuenta vive adentro de la grilla.
        //
        // LO QUE SE HACE AHORA: manejar la perilla de verdad,
        // `setGridOption('rowHeight', n)` + `resetRowHeights()`, con lo cual
        // ag-grid recalcula alturas, posiciones, altura total y
        // virtualizacion — todo consistente, y el scroll se comporta. La
        // unica gracia es CONSEGUIR la api: esta grilla no publica ningun
        // handle (a diferencia de `tablas/desktop.py`, que se guarda
        // `window.__agApi` en su `onGridReady`), asi que se sube por el
        // fiber de React desde `.ag-root-wrapper` hasta el `stateNode` que
        // la tiene. Verificado en vivo: aparece 5 niveles arriba.
        //
        // Ojo con el timing: despues de `resetRowHeights()` las posiciones
        // se acomodan en el frame SIGUIENTE (medido: justo despues de la
        // llamada los translateY siguen con el espaciado viejo). No es un
        // bug ni hay que compensarlo — solo no sirve medir en la misma
        // vuelta.
        function docDeAgGrid(elemento) {
            if (!elemento || !elemento.querySelector) return null;
            var ifr = elemento.querySelector('iframe[title="st_aggrid.AgGrid.agGrid"]');
            if (!ifr) return null;
            try {
                var d = ifr.contentDocument;
                return (d && d.querySelector('.ag-root-wrapper')) ? d : null;
            } catch (err) { return null; }   // cross-origin en algun despliegue raro
        }
        function esApiGrid(o) {
            return o && typeof o === 'object'
                   && typeof o.setGridOption === 'function'
                   && typeof o.getGridOption === 'function'
                   && typeof o.resetRowHeights === 'function';
        }
        function apiDeAgGrid(gdoc) {
            if (!gdoc) return null;
            // Cacheada en el documento del iframe: Streamlit lo recrea entero
            // en cada rerun, asi que la cache muere sola cuando corresponde.
            var cache = gdoc.__disenoAgApi;
            if (cache) {
                try {
                    if (typeof cache.isDestroyed !== 'function' || !cache.isDestroyed()) return cache;
                } catch (err) {}
                gdoc.__disenoAgApi = null;
            }
            var root = gdoc.querySelector('.ag-root-wrapper');
            if (!root) return null;
            var fk = null;
            for (var k in root) { if (k.indexOf('__reactFiber$') === 0) { fk = k; break; } }
            if (!fk) return null;
            var f = root[fk], pasos = 0;
            while (f && pasos < 40) {
                var sn = f.stateNode;
                if (sn && typeof sn === 'object') {
                    if (esApiGrid(sn)) { gdoc.__disenoAgApi = sn; return sn; }
                    for (var kk in sn) {
                        try {
                            if (esApiGrid(sn[kk])) { gdoc.__disenoAgApi = sn[kk]; return sn[kk]; }
                        } catch (err2) {}   // getters que tiran al leerse
                    }
                }
                f = f.return; pasos++;
            }
            return null;
        }
        function altoFilaDe(gdoc) {
            var api = apiDeAgGrid(gdoc);
            if (!api) return null;
            try {
                var h = api.getGridOption('rowHeight');
                return (isFinite(h) && h > 0) ? h : null;
            } catch (err) { return null; }
        }
        function filasQueEntran(gdoc, alto) {
            var vp = gdoc && gdoc.querySelector('.ag-body-viewport');
            if (!vp || !alto) return null;
            return Math.floor(vp.getBoundingClientRect().height / alto);
        }
        function aplicarAltoFila(elemento, registro) {
            var destino = registro.filaAlto && registro.filaAlto.actual;
            if (!destino) return;
            var api = apiDeAgGrid(docDeAgGrid(elemento));
            if (!api) return;
            try {
                if (api.getGridOption('rowHeight') === destino) return;   // idempotente
                api.setGridOption('rowHeight', destino);
                api.resetRowHeights();
            } catch (err) {}
        }

        // ── Override de TEXTO (efimero, como todo el modo diseno) ────────
        // `registro.texto` existia en registroPara() desde la fase A y
        // nunca se habia usado — quedo previsto para esto.
        // Se REAPLICA en cada tick (aplicarEstado corre desde el poll de
        // 150ms): Plotly redibuja su SVG entero al cambiar de granularidad
        // y AgGrid recicla las filas al scrollear, asi que un textContent
        // escrito una sola vez se pierde solo. Idempotente por el `!==`.
        function aplicarTextoOverride(elemento, registro) {
            var t = registro.texto;
            if (!t || t.actual === null || t.actual === undefined) return;
            // Nunca sobre un nodo con hijos ELEMENTO: textContent los
            // borraria de cuajo (una tarjeta entera reducida a una cadena).
            if (elemento.children && elemento.children.length) return;
            if (t.original === null) t.original = elemento.textContent || '';
            if ((elemento.textContent || '') !== t.actual) {
                elemento.textContent = t.actual;
            }
        }

        function restaurarTexto(elemento, registro) {
            var t = registro.texto;
            if (!t || t.original === null || t.original === undefined) return;
            if (elemento.children && elemento.children.length) return;
            if ((elemento.textContent || '') !== t.original) {
                elemento.textContent = t.original;
            }
        }

        function aplicarEstado(elemento, registro) {
            // snapshot para "ver original", una sola vez (primer touch de la key)
            if (registro.cssTextOriginal === null) {
                registro.cssTextOriginal = elemento.style.cssText || '';
            }
            if (registro.verOriginalActivo) {
                elemento.style.cssText = registro.cssTextOriginal;
                restaurarTexto(elemento, registro);
                return;
            }
            // ── Hoja de texto: SVG de Plotly, o nodo dentro del iframe de
            // AgGrid. Se corta ACA, antes de destinosDeEstilo(): esas
            // redirecciones estan pensadas para wrappers de widgets de
            // Streamlit (regla #154) y no tienen sentido sobre un <text>
            // — el nodo ES el texto, no hay a quien redirigir.
            // Y en SVG el color se pinta con `fill`: sin traducir, mover el
            // color no hacia absolutamente nada visible.
            var esSVGTexto = !!elemento.ownerSVGElement;
            var esDeOtroDoc = elemento.ownerDocument !== doc;
            if (esSVGTexto || esDeOtroDoc) {
                for (var pt in registro.cambios) {
                    var pr = (esSVGTexto && pt === 'color') ? 'fill' : pt;
                    elemento.style.setProperty(pr, registro.cambios[pt], 'important');
                }
                aplicarTextoOverride(elemento, registro);
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
            // Reaplicado defensivo (cada 150ms, ver sync()): un Plotly que
            // recién se re-montó tras un rerun real vuelve con su ancho/
            // alto de Python — hay que re-empujar el tamaño elegido igual
            // que el resto de `cambios`, o el chart "salta" de vuelta a su
            // tamaño original hasta el próximo drag.
            if (registro.cambios.width !== undefined || registro.cambios.height !== undefined) {
                sincronizarContenidoRedimensionable(elemento,
                    registro.cambios.width ? parseInt(registro.cambios.width, 10) : null,
                    registro.cambios.height ? parseInt(registro.cambios.height, 10) : null);
            }
            // Mismo reaplicado defensivo que el de arriba, y por un motivo
            // mas fuerte: ag-grid recicla filas al scrollear y las reescribe
            // con SU rowHeight. La guarda de idempotencia esta adentro.
            aplicarAltoFila(elemento, registro);
            aplicarTransform(elemento, registro);
            // Vale tambien para HTML normal (un `.cp-rank-tit`, el label de
            // un boton): la guarda de "sin hijos elemento" que trae adentro
            // es la que decide si el nodo es de verdad una hoja de texto.
            aplicarTextoOverride(elemento, registro);
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
                    var nuevoAncho = null, nuevoAlto = null;
                    if (modo.indexOf('e') !== -1) {
                        nuevoAncho = Math.max(60, Math.round(startW + dx));
                        establecerCambio(vivo.el, vivo.registro, 'width', nuevoAncho + 'px');
                    }
                    if (modo.indexOf('s') !== -1) {
                        nuevoAlto = Math.max(40, Math.round(startH + dy));
                        establecerCambio(vivo.el, vivo.registro, 'height', nuevoAlto + 'px');
                    }
                    // En vivo, arrastrando: mismo mecanismo que el reaplicado
                    // defensivo de aplicarEstado(), pero con los numeros del
                    // gesto actual (mas fresco que esperar al proximo tick de
                    // 150ms — se veria trabado un cuarto de segundo detras
                    // del cursor).
                    sincronizarContenidoRedimensionable(vivo.el, nuevoAncho, nuevoAlto);
                }
                trackear(vivo.el);
                actualizarReadouts(vivo.el, vivo.registro);
            }
            // Las tarjetas con AgGrid (Ranking de proveedores, Documentos, ...)
            // tienen la grilla ocupando la mayor parte del cuerpo: mover o
            // agrandar la tarjeta cruza el cursor sobre ese iframe a los
            // pocos pixeles. `mousemove`/`mouseup` de un iframe NO suben al
            // documento padre (misma frontera que arquitectura.md #185, ahi
            // para `contextmenu`) — sin este enganche el arrastre se
            // congelaba apenas el cursor entraba a la tabla. Se instala y
            // desinstala por gesto (no hace falta el poll de `sync()`: un
            // drag no sobrevive a un rerun de Streamlit).
            var ganchosIframe = [];
            var ifsArrastre = doc.querySelectorAll('iframe');
            for (var fi = 0; fi < ifsArrastre.length; fi++) {
                var frameA = ifsArrastre[fi], fdocA = null;
                try { fdocA = frameA.contentDocument; } catch (e) { continue; }
                if (!fdocA) continue;
                (function (frame, fdoc) {
                    var reenviarMove = function (ev) {
                        var rf = frame.getBoundingClientRect();
                        onMove({ clientX: rf.left + ev.clientX, clientY: rf.top + ev.clientY });
                    };
                    var reenviarUp = function () { onUp(); };
                    fdoc.addEventListener('mousemove', reenviarMove);
                    fdoc.addEventListener('mouseup', reenviarUp);
                    ganchosIframe.push({ fdoc: fdoc, move: reenviarMove, up: reenviarUp });
                })(frameA, fdocA);
            }

            function onUp() {
                doc.body.style.userSelect = '';
                doc.body.style.cursor = cursorPrevio;
                doc.removeEventListener('mousemove', onMove);
                doc.removeEventListener('mouseup', onUp);
                for (var gi = 0; gi < ganchosIframe.length; gi++) {
                    ganchosIframe[gi].fdoc.removeEventListener('mousemove', ganchosIframe[gi].move);
                    ganchosIframe[gi].fdoc.removeEventListener('mouseup', ganchosIframe[gi].up);
                }
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

        function construirBloqueCSS(key, elemento, registro, sub, subTexto) {
            // ── Hoja de texto: el export NO es CSS de estilos/ ───────────
            // Devolver el bloque de siempre seria mentir dos veces: en
            // Plotly el SVG se dibuja en el servidor y esas propiedades
            // salen de Python; en AgGrid el nodo vive DENTRO de un iframe,
            // donde una regla de `estilos/` no entra ni por casualidad.
            // Pegarlo no haria nada y el "no hace lo que probe" tardaria
            // media hora en diagnosticarse — exactamente la regla #169.
            // Asi que se entrega el DESTINO, no un selector inutil.
            if (subTexto) {
                var props = [];
                for (var p in registro.cambios) {
                    props.push('  ' + p + ': ' + registro.cambios[p] + ';');
                }
                var txtNuevo = (registro.texto && registro.texto.actual !== null
                                && registro.texto.actual !== undefined)
                    ? registro.texto.actual : null;
                var out = [];
                if (subTexto.tipo === 'svgtext') {
                    out.push('/* Texto de PLOTLY — «' + subTexto.txt + '»');
                    out.push('   Esto NO va en estilos/: Plotly dibuja el SVG en el');
                    out.push('   servidor y el tamano/color del texto sale de Python.');
                    out.push('   Buscar la figura en graficos/ y tocar su layout:');
                    out.push('     fig.update_layout(font=dict(size=..., color=...))');
                    out.push('     o el eje puntual: fig.update_xaxes(tickfont=...)');
                    out.push('   Color: desde tema.py, nunca un #hex suelto (regla #1). */');
                } else {
                    out.push('/* Texto de AGGRID — «' + subTexto.txt + '»');
                    out.push('   Esto NO va en estilos/: la grilla corre dentro de un');
                    out.push('   IFRAME y una regla del documento padre no lo alcanza.');
                    out.push('   Va en el `custom_css` del AgGrid (mismo modulo que');
                    out.push('   arma la tabla), o en el column_def si es el rotulo:');
                    out.push('     custom_css={".ag-header-cell-text": {...}}');
                    out.push('   Color: desde tema.py (regla #1). */');
                }
                if (props.length) {
                    out.push('/* Lo que se probo en pantalla: */');
                    out.push('/*');
                    out.push.apply(out, props);
                    out.push('*/');
                }
                if (txtNuevo !== null) {
                    out.push('/* Texto probado: «' + txtNuevo + '»');
                    out.push('   (preview: el valor real sale de los datos o de Python) */');
                }
                return out.join('\\n');
            }
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
            // El alto de fila probado tampoco es CSS (ver aplicarAltoFila):
            // va al gridOptions de Python. Se emite aunque no haya ni una
            // propiedad CSS tocada — es justo el caso de "solo vine a
            // achicar las filas".
            var notaFila = '';
            if (registro.filaAlto && registro.filaAlto.actual) {
                notaFila = '/* AgGrid — alto de fila probado: '
                    + registro.filaAlto.actual + 'px (era '
                    + (registro.filaAlto.original || '?') + 'px)\\n'
                    + '   NO es CSS: va en el gridOptions de la tabla, en Python\\n'
                    + '     "rowHeight": ' + registro.filaAlto.actual + '\\n'
                    + '   Y su gemela en graficos/alturas.py, que es de donde sale\\n'
                    + '   el height= del grid:  por_filas(n, px_fila='
                    + registro.filaAlto.actual + ', ...)\\n'
                    + '   Las dos juntas o ninguna: si se cambia una sola, el alto\\n'
                    + '   del marco deja de coincidir con lo que ocupan las filas. */';
            }
            if (!bloques.length) return notaFila || null;

            // Las notas se emiten solo si esa redireccion LE PASO a algo que
            // se esta copiando: `redirigido`/`hayTextoPropio` describen al
            // elemento (tiene botones adentro, sus labels traen <p> propio),
            // no al bloque. Sin el chequeo del grupo, un export de pura caja
            // — el caso tipico de Unificar, que solo mueve esquinas y ancho —
            // salia con un "texto redirigido al <p> del label" abajo que no
            // aplicaba a ninguna de las lineas de arriba.
            var notas = [];
            if (redirigido && Object.keys(estBoton).length) notas.push('caja redirigida a los botones internos');
            if (hayTextoPropio && Object.keys(estTexto).length) notas.push('texto redirigido al <p> del label, que trae su propio font-size/weight');
            var pie = notas.length
                ? '\\n/* ' + notas.join(' — ') + ' — ver destinosDeEstilo()/extenderATexto() en _diseno_js.py */'
                : '';

            var encabezado = '/* copiado del modo diseño — ' + key + (sub ? ' .' + sub : '') + ' */';
            return encabezado + '\\n' + bloques.join('\\n\\n') + pie
                   + (notaFila ? '\\n\\n' + notaFila : '');
        }

        // La union se copia SIEMPRE de a dos bloques: pegar uno solo deja
        // media costura (una esquina redondeada contra una recta, y el
        // hueco a medio cerrar). El bloque de la pineada ya sale de
        // construirBloqueCSS() como cualquier otro cambio — esto agrega el
        // de la otra mitad, con la advertencia de que el CSS hace que se
        // VEAN como una, no que lo sean.
        function bloquesDeUnion(key) {
            var us = unionesDe(key), out = [];
            us.forEach(function(u) {
                var otra = (u.a === key) ? u.b : u.a;
                var elO = porKeyReal(otra);
                if (!elO) return;
                out.push('/* UNIFICAR - la otra mitad: «' + otra + '», pegada en '
                    + PROPS_UNION[u.eje].nombre + ' a «' + key + '».\\n'
                    + '   Los dos bloques van juntos: con uno solo queda media costura.\\n'
                    + '   Y ojo con lo que hace: las deja VER como una sola tarjeta.\\n'
                    + '   Unificarlas de verdad — un solo st.container con las dos\\n'
                    + '   cosas adentro — es un cambio de Python en graficos/. */');
                var b = construirBloqueCSS(otra, elO, registroPara(otra), '', null);
                if (b) out.push(b);
            });
            return out.length ? out.join('\\n') : null;
        }

        // Duplica (a proposito, ver docstring de diseno.py) el fallback de
        // copiarTexto() de _inspector_js.py: este script corre en OTRO
        // iframe de inyectar_html, sin acceso a esa funcion local.
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
            headerKey.textContent = res.subTexto
                ? (key + ' «' + res.subTexto.txt + '»')
                : (res.sub ? (key + ' .' + res.sub) : key);
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
                // Son DOS contornos violetas de fuentes distintas: este overlay
                // (div aparte, 4px afuera) y el `outline` INLINE que el
                // inspector le pone al elemento resaltado. Apagar solo el
                // primero dejaba el segundo encima del borde que se estaba
                // editando — se veia como "el boton no hace nada". Regla #254.
                if (win.__inspectorSetResaltadoOculto) {
                    win.__inspectorSetResaltadoOculto(win.__disenoContornoOculto);
                }
            });

            // Empujar/soltar el lienzo. Va al lado del de contorno: los dos
            // responden a "no me deja ver", uno por encima del elemento y
            // el otro por el costado.
            var btnEmpujar = doc.createElement('button');
            btnEmpujar.title = 'Encoger la app para que el panel no la tape'
                + ' (ojo: cambia el ancho util y puede disparar las @media de movil)';
            btnEmpujar.textContent = win.__disenoState.empujarLienzo ? '⇥' : '⇤';
            btnEmpujar.style.cssText = 'background:' + (win.__disenoState.empujarLienzo ? '#3C3489' : '#2A2A35')
                + ';color:#fff;border:0;border-radius:4px;padding:4px 7px;font:600 11px sans-serif;cursor:pointer;flex:0 0 auto';
            btnEmpujar.addEventListener('click', function() {
                win.__disenoState.empujarLienzo = !win.__disenoState.empujarLienzo;
                btnEmpujar.textContent = win.__disenoState.empujarLienzo ? '⇥' : '⇤';
                btnEmpujar.style.background = win.__disenoState.empujarLienzo ? '#3C3489' : '#2A2A35';
                aplicarReserva(win.__disenoState.empujarLienzo);
            });

            header.appendChild(headerKey);
            header.appendChild(btnEmpujar);
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
            var hojasTxt = hojasDeTexto(key);
            if (cadenaDiseno.length > 1 || hojasSub.length || hojasTxt.length) {
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
                // Hojas de TEXTO en ambar, para que se distingan de un
                // vistazo de las hojas-por-clase (azules): no se estilan
                // igual ni se exportan al mismo sitio — una va a estilos/
                // y estas dos a Python. Se rotulan con su texto, no con un
                // selector: ".xtick" no le dice nada a nadie, «ago 25» si.
                var ETIQ_TXT = { svgtext: '📈', agtext: '▦' };
                hojasTxt.forEach(function(h) {
                    var st = res.subTexto;
                    var esActualTxt = !!(st && st.tipo === h.tipo && st.idx === h.idx);
                    var fila = doc.createElement('div');
                    fila.style.cssText = 'display:flex;align-items:center;gap:4px;padding:2px 0;padding-left:'
                        + (cadenaDiseno.length * 11) + 'px;white-space:nowrap';
                    var rama = doc.createElement('span');
                    rama.textContent = '└';
                    rama.style.cssText = 'color:#3f3f4c;flex-shrink:0;font-size:11px';
                    fila.appendChild(rama);
                    var nodo = doc.createElement(esActualTxt ? 'span' : 'button');
                    var corto = h.txt.length > 22 ? h.txt.slice(0, 21) + '…' : h.txt;
                    nodo.textContent = ETIQ_TXT[h.tipo] + ' ' + corto;
                    nodo.title = (h.tipo === 'svgtext'
                        ? 'Texto de Plotly (SVG). Se dibuja en el servidor: el cambio real va en graficos/.'
                        : 'Texto de AgGrid (dentro de su iframe). El cambio real va en el custom_css / la columna, en Python.');
                    nodo.style.cssText = 'font:11px "Courier New",monospace;background:transparent;border:0;padding:1px 3px;border-radius:3px;'
                        + 'color:' + (esActualTxt ? '#e4e4e8' : '#e0a35c') + ';'
                        + 'font-weight:' + (esActualTxt ? '700' : '400')
                        + (esActualTxt ? '' : ';cursor:pointer');
                    if (!esActualTxt) {
                        nodo.addEventListener('mouseenter', function() { nodo.style.background = '#2A2A35'; });
                        nodo.addEventListener('mouseleave', function() { nodo.style.background = 'transparent'; });
                        nodo.addEventListener('click', function() { bajarASubTexto(h); });
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
            // inyectar_html — arquitectura.md § Reglas #39) no hay nada
            // mas en pantalla para seleccionar, a diferencia del inspector
            // que ya tiene su <pre> visible. Sin este textarea, "Ctrl+C"
            // seria un mensaje que miente.
            var taManual = doc.createElement('textarea');
            taManual.readOnly = true;
            taManual.style.cssText = 'display:none;width:100%;height:90px;margin-top:6px;background:#1c1c24;color:#e4e4e8;border:1px solid #34343f;border-radius:4px;padding:6px;font:10px/1.4 "Courier New",monospace;box-sizing:border-box';
            btnCopiarCSS.addEventListener('click', function() {
                var ctx = elementoActivo();
                var bloque = ctx ? construirBloqueCSS(ctx.key, ctx.el, ctx.registro,
                                                      ctx.sub, ctx.subTexto) : null;
                // Solo con el pin en la TARJETA: con sub-pin el export es
                // el de un hijo (o el destino de un texto de Plotly/AgGrid)
                // y la union no tiene nada que ver con eso.
                if (ctx && !ctx.sub && !ctx.subTexto) {
                    var mitadB = bloquesDeUnion(ctx.key);
                    if (mitadB) bloque = (bloque ? bloque + '\\n\\n' : '') + mitadB;
                }
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

            // ── Cambiar el TEXTO (preview efimero) ───────────────────────
            // Solo si el nodo pineado es de verdad una hoja de texto (sin
            // hijos elemento): sobre un contenedor, escribir textContent
            // borraria todo lo de adentro.
            // Es PREVIEW y se dice explicito en el caption: el texto real
            // sale de los datos (una celda de AgGrid), de Python (un
            // rotulo de eje) o de un `st.markdown` — nunca del navegador.
            if (elemento && (!elemento.children || !elemento.children.length)) {
                var cajaTxt = doc.createElement('div');
                cajaTxt.style.cssText = 'margin-bottom:10px;padding:8px 9px;background:#1c1c24;border:1px solid #2a2a35;border-radius:6px';
                var lblTxt = doc.createElement('div');
                lblTxt.textContent = 'Texto (preview)';
                lblTxt.style.cssText = 'font:600 10px sans-serif;color:#8a8a99;margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em';
                cajaTxt.appendChild(lblTxt);
                var filaTxt = doc.createElement('div');
                filaTxt.style.cssText = 'display:flex;gap:5px;align-items:center';
                var inpTxt = doc.createElement('input');
                inpTxt.type = 'text';
                inpTxt.value = (registro.texto && registro.texto.actual !== null
                                && registro.texto.actual !== undefined)
                    ? registro.texto.actual : (elemento.textContent || '');
                inpTxt.style.cssText = 'flex:1;min-width:0;background:#12121a;color:#e4e4e8;border:1px solid #33333f;border-radius:4px;padding:5px 7px;font:11px sans-serif';
                inpTxt.addEventListener('input', function() {
                    var a = elementoActivo();
                    if (!a) return;
                    if (a.registro.texto.original === null) {
                        a.registro.texto.original = a.el.textContent || '';
                    }
                    a.registro.texto.actual = inpTxt.value;
                    aplicarEstado(a.el, a.registro);
                    // El ancla se direcciona por texto: sin esto, el
                    // siguiente tick no encuentra el nodo que acaba de
                    // cambiar de nombre y el pin se "pierde" solo.
                    if (win.__disenoState.sub && win.__disenoState.sub.tipo) {
                        win.__disenoState.sub.txtVivo = inpTxt.value;
                    }
                });
                var btnTxtRev = doc.createElement('button');
                btnTxtRev.textContent = '↺';
                btnTxtRev.title = 'Volver al texto original';
                btnTxtRev.style.cssText = 'background:#2A2A35;color:#fff;border:0;border-radius:4px;padding:5px 8px;font:600 11px sans-serif;cursor:pointer;flex:0 0 auto';
                btnTxtRev.addEventListener('click', function() {
                    var a = elementoActivo();
                    if (!a) return;
                    restaurarTexto(a.el, a.registro);
                    a.registro.texto.actual = null;
                    if (win.__disenoState.sub && win.__disenoState.sub.tipo) {
                        win.__disenoState.sub.txtVivo = null;
                    }
                    inpTxt.value = a.el.textContent || '';
                });
                filaTxt.appendChild(inpTxt);
                filaTxt.appendChild(btnTxtRev);
                cajaTxt.appendChild(filaTxt);
                var capTxt = doc.createElement('div');
                capTxt.textContent = res.subTexto
                    ? (res.subTexto.tipo === 'svgtext'
                        ? 'Solo preview. El rótulo real lo dibuja Plotly desde graficos/.'
                        : 'Solo preview. El valor real sale de los datos o del column_def.')
                    : 'Solo preview: no persiste al recargar.';
                capTxt.style.cssText = 'margin-top:5px;font:10px sans-serif;color:#7a7a88;line-height:1.35';
                cajaTxt.appendChild(capTxt);
                panel.appendChild(cajaTxt);
            }

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
                avisoMock.textContent = esCopia(key)
                    ? 'Copia del modo diseño: sirve para juzgar espaciado y densidad, pero es HTML muerto — los widgets de adentro (selectbox, tabla) no responden. Se va al recargar.'
                    : 'Insertado por el modo diseño: no existe en el código ni en estilos/. Se va al recargar.';
                panel.appendChild(avisoMock);
            }

            // El tamaño de un Plotly/AgGrid SÍ se ve arrastrando las manijas
            // (arquitectura.md #175) pero el número real que hay que llevar
            // al código NO es CSS — "Copiar CSS" no sirve para esto.
            var contenidoResz = contenidoRedimensionable(elemento);
            if (contenidoResz) {
                var avisoResz = doc.createElement('div');
                avisoResz.style.cssText = 'font:11px/1.4 -apple-system,sans-serif;color:#9385ec;background:#1c1c24;border:1px solid #34343f;border-radius:4px;padding:6px 7px;margin-bottom:10px';
                avisoResz.textContent = contenidoResz.tipo === 'plotly'
                    ? 'El tamaño de un gráfico Plotly vive en Python (fig.update_layout / graficos/alturas.py), no en CSS — "Copiar CSS" no lo va a incluir. Anotá el "Tamaño" de abajo y llevalo ahí.'
                    : 'El tamaño de una tabla AgGrid vive en Python (el height= de tablas/), no en CSS — "Copiar CSS" no lo va a incluir. Anotá el "Tamaño" de abajo y llevalo ahí. Para las FILAS usá "Alto de fila": tampoco es CSS (mueve la perilla rowHeight de la propia grilla), pero el botón de copiar te deja el número listo.';
                panel.appendChild(avisoResz);
            }

            var tamVal = spanValor('');
            panel.appendChild(filaSoloLectura('Tamaño', tamVal));
            var posVal = spanValor('');
            panel.appendChild(filaSoloLectura('Posición (nudge)', posVal));
            // Se actualiza en cada tick desde actualizarReadouts(); nace
            // oculta y solo aparece cuando hay recorte de verdad.
            var recorteVal = spanValor('');
            recorteVal.style.color = '#f0a500';
            var filaRecorte = filaSoloLectura('Recortado por', recorteVal);
            filaRecorte.style.display = 'none';
            panel.appendChild(filaRecorte);
            panel.__tamVal = tamVal;
            panel.__posVal = posVal;
            panel.__recorteVal = recorteVal;
            panel.__filaRecorte = filaRecorte;

            // ── Alto de fila (solo AgGrid) ────────────────────────
            // Preview de `rowHeight`: lo unico del panel que no se toca
            // arrastrando ni se copia como CSS. Ver aplicarAltoFila().
            // Sin api alcanzable NO se dibuja el control: un slider que
            // mueve el DOM pero no la virtualizacion se ve bien hasta el
            // primer scroll y despues miente (ver el comentario de
            // aplicarAltoFila). Mejor no ofrecerlo que ofrecerlo roto.
            var gdocPanel = docDeAgGrid(elemento);
            if (gdocPanel && apiDeAgGrid(gdocPanel)) {
                var altoAhora = altoFilaDe(gdocPanel);
                if (registro.filaAlto.original === null && altoAhora) {
                    registro.filaAlto.original = altoAhora;
                }
                var base = registro.filaAlto.actual || altoAhora
                           || registro.filaAlto.original || 35;
                var inpFila = rango(16, 56, 1, base);
                var filaLbl = spanValor('');
                function pintarFilaLbl(v) {
                    var n = filasQueEntran(gdocPanel, v);
                    filaLbl.textContent = Math.round(v) + 'px'
                        + (n ? ' · entran ' + n + ' filas' : '');
                }
                pintarFilaLbl(base);
                inpFila.addEventListener('input', function() {
                    var ctx = elementoActivo(); if (!ctx) return;
                    var v = parseInt(inpFila.value, 10);
                    ctx.registro.filaAlto.actual = v;
                    aplicarAltoFila(ctx.el, ctx.registro);
                    pintarFilaLbl(v);
                });
                panel.appendChild(filaControl('Alto de fila (AgGrid)', inpFila,
                                              filaLbl, function() {
                    var ctx = elementoActivo(); if (!ctx) return;
                    var orig = ctx.registro.filaAlto.original;
                    if (orig) {
                        // Restaurar es aplicar el original y recien despues
                        // soltar el override: si se pone `actual = null` a
                        // secas, las filas se quedan con el alto probado
                        // hasta que ag-grid decida redibujar solo.
                        ctx.registro.filaAlto.actual = orig;
                        aplicarAltoFila(ctx.el, ctx.registro);
                        inpFila.value = orig;
                        pintarFilaLbl(orig);
                    }
                    ctx.registro.filaAlto.actual = null;
                }));
            }

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

            // Familia tipografica. La lista NO es libre: son las pilas que el
            // proyecto ya usa mas las webfont-safe que existen en cualquier
            // maquina. Un <select> con 200 fuentes del sistema mentiria — lo
            // que se elija tiene que poder pegarse en estilos/ y verse igual
            // en la laptop del usuario final, que no es esta. Ver regla #255.
            var FUENTES = [
                ['', '(la que hereda)'],
                ['-apple-system, "Segoe UI", sans-serif', 'Sistema (la de la app)'],
                ['"Segoe UI", Roboto, sans-serif', 'Segoe UI'],
                ['Georgia, "Times New Roman", serif', 'Georgia (serif)'],
                ['"Courier New", monospace', 'Courier (mono)'],
                ['Arial, Helvetica, sans-serif', 'Arial'],
                ['Verdana, Geneva, sans-serif', 'Verdana'],
                ['Impact, "Arial Black", sans-serif', 'Impact (titular)']
            ];
            var selFuente = doc.createElement('select');
            selFuente.style.cssText = 'width:100%;background:#1c1c24;color:#e4e4e8;'
                + 'border:1px solid #34343f;border-radius:4px;padding:5px 6px;'
                + 'font:11px sans-serif;cursor:pointer';
            var fuenteActual = registro.cambios['font-family'] || '';
            FUENTES.forEach(function(par) {
                var o = doc.createElement('option');
                o.value = par[0];
                o.textContent = par[1];
                // Previsualiza en su propia fuente: elegir "Georgia" de una
                // lista escrita toda en sans-serif es elegir a ciegas.
                if (par[0]) o.style.fontFamily = par[0];
                if (par[0] === fuenteActual) o.selected = true;
                selFuente.appendChild(o);
            });
            selFuente.addEventListener('change', function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'font-family',
                    selFuente.value || null);
            });
            panel.appendChild(filaControl('Tipo de letra', selFuente, spanValor(''), function() {
                var ctx = elementoActivo(); if (!ctx) return;
                establecerCambioEstilo(ctx.el, ctx.registro, 'font-family', null);
                rehacerPanel();
            }));

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

            // ---- unificar: dos tarjetas vecinas como una sola ----
            panel.appendChild(seccion('Unificar'));

            var capUnir = doc.createElement('div');
            capUnir.style.cssText = 'font-size:10px;line-height:1.45;color:#6f6f7a;margin:6px 0 2px';
            capUnir.textContent = 'Las pega: cierra el hueco y saca las esquinas del lado que se tocan.'
                + ' Es el look — unirlas de verdad (un solo st.container) es un cambio de Python.';
            panel.appendChild(capUnir);

            var unisDeKey = unionesDe(key);
            unisDeKey.forEach(function(u) {
                var otra = (u.a === key) ? u.b : u.a;
                var filaU = doc.createElement('div');
                filaU.style.cssText = 'display:flex;align-items:center;gap:6px;margin-top:6px';
                var txtU = doc.createElement('div');
                txtU.style.cssText = 'flex:1;min-width:0;font:10px/1.3 "Courier New",monospace;color:#9385ec;word-break:break-all';
                txtU.textContent = (u.a === key ? '\u25b8 ' : '\u25c2 ') + otra;
                txtU.title = 'Pegada en ' + PROPS_UNION[u.eje].nombre
                    + ' (hueco cerrado: ' + u.hueco + 'px)';
                var btnSep = doc.createElement('button');
                btnSep.textContent = 'Separar';
                btnSep.style.cssText = 'flex:0 0 auto;background:#1c1c24;color:#e4e4e8;border:1px solid #34343f;border-radius:4px;padding:5px 8px;font:11px sans-serif;cursor:pointer';
                btnSep.addEventListener('click', function() {
                    separarUnion(u);
                    panel.dataset.builtForKey = '';
                    sync();
                });
                filaU.appendChild(txtU);
                filaU.appendChild(btnSep);
                panel.appendChild(filaU);
            });

            // La lista de vecinas vive en su propia caja y se repinta sola
            // (ver pintarVecinas): depende de rects, no de la key pineada.
            var cajaVec = doc.createElement('div');
            panel.appendChild(cajaVec);
            panel.__cajaVecinas = cajaVec;
            panel.__vecinasDe = key;
            panel.__vecinasFirma = '';
            pintarVecinas();

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

            // Aviso de "Copia", puesto a pedido (2026-08-31): el pin NO
            // salta al clon al crearlo (`agregarMock` no toca
            // `__inspectorPinned`), y el clon es HTML muerto con
            // `pointer-events:none` — no se puede seleccionar haciendo
            // clic en él. Sin este aviso, arrastrar "Mover" después de
            // "+ Copia" mueve el ORIGINAL creyendo que se mueve el clon,
            // y como el clon se queda quieto en el lugar de siempre, el
            // original "desaparece" de donde se lo busca — reportado tal
            // cual, confirmado reproduciendo el gesto con eventos reales.
            var avisoCopia = doc.createElement('div');
            avisoCopia.style.cssText = 'font:11px/1.4 -apple-system,sans-serif;color:#9385ec;background:#1c1c24;border:1px solid #34343f;border-radius:4px;padding:6px 7px;margin-top:6px';
            avisoCopia.textContent = '"Copia" queda fija: no se puede seleccionar ni mover — es solo para ver el espaciado. Arrastrar/editar después de crearla sigue tocando el ORIGINAL (el pin no salta al clon).';
            panel.appendChild(avisoCopia);

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
            // Aviso de recorte: se recalcula en cada tick porque depende del
            // tamano de AHORA — aparece a mitad de un arrastre, que es
            // justo cuando sirve.
            if (panel.__filaRecorte) {
                var rec = ancestroQueRecorta(elemento);
                if (rec) {
                    var ejes = [];
                    if (rec.x > 1) ejes.push(rec.x + 'px a la derecha');
                    if (rec.y > 1) ejes.push(rec.y + 'px abajo');
                    panel.__recorteVal.textContent = ejes.join(' + ');
                    panel.__filaRecorte.title = 'El ancestro `' + rec.key
                        + '` tiene overflow ' + rec.overflowX + '/' + rec.overflowY
                        + ' y corta lo que sobresale: el elemento SI crecio, pero'
                        + ' esa parte no se dibuja.';
                    panel.__filaRecorte.firstChild.textContent = 'Recortado por ' + rec.key;
                    panel.__filaRecorte.style.display = 'flex';
                } else {
                    panel.__filaRecorte.style.display = 'none';
                }
            }
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
                // Salir del modo diseno tiene que devolver la app a su ancho:
                // la <style> de la reserva vive en el <head> y sobrevive al
                // apagado (para eso se puso ahi), asi que hay que apagarla a
                // mano o el lienzo queda encogido sin panel que lo explique.
                aplicarReserva(false);
                return;
            }
            // Antes de resolver el pin: un mock puede SER el pineado, y
            // Streamlit se lo lleva cuando re-renderiza su rama.
            reponerMocks();
            // Despues de reponerMocks (que puede insertar nodos y correr
            // los rects) y antes de resolver el pin: las dos mitades de una
            // union se reaplican aunque ninguna este pineada — el
            // aplicarEstado() del final del tick solo alcanza a la pineada.
            reaplicarUniones();
            // Barato por el guard `__disenoEnganchado`, y hay que reintentar
            // en cada tick: Streamlit recrea el iframe de AgGrid en cada
            // rerun y el listener se va con el documento viejo.
            engancharIframes();
            // Antes de resolver: si el inspector fijo un nodo distinto, el
            // sub tiene que reflejar ESE nodo y no el anterior.
            sincronizarSubConElPin();
            var res = elementoPineado();

            // Panel: colapsado se ve igual (una pill chica) haya o no algo
            // pineado. El overlay/manijas del elemento pineado (mas abajo)
            // son independientes de esto — colapsar el panel no las apaga.
            // Colapsado el panel es una pill chica que no tapa nada: la
            // reserva sobraria y dejaria una franja muerta a la derecha.
            aplicarReserva(win.__disenoState.empujarLienzo
                && !win.__disenoState.panelColapsado);
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
            // 1 de cada 7 ticks (~1 seg): la lista de vecinas se arma con
            // rects y el layout se acomoda despues del pin — ver
            // pintarVecinas(), que corta sola si no cambio nada.
            win.__disenoState.tick = (win.__disenoState.tick || 0) + 1;
            if (win.__disenoState.tick % 7 === 0) pintarVecinas();
        }

        // rerun-safety: el iframe de inyectar_html se recrea en cada
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
        if (win.__disenoClickBlocker) { doc.removeEventListener('click', win.__disenoClickBlocker, true); }

        win.__disenoScrollHandler = sync;
        win.__disenoResizeHandler = sync;
        win.__disenoKeydownHandler = function(e) {
            if (e.altKey && (e.key === 'd' || e.key === 'D') && disenoActivo()) {
                win.__disenoState.panelColapsado = !win.__disenoState.panelColapsado;
                panel.dataset.builtForKey = '';
                sync();
            }
        };
        // Captura en el documento PADRE, antes de que el click baje hasta el
        // arbol de React de Streamlit: parar la propagacion aca hace que el
        // widget real nunca se entere del click (no le hace falta tocar
        // preventDefault de un <a> — los botones del rail son <button>
        // nativos manejados por el listener delegado de React, que vive mas
        // abajo en el arbol y jamas ve un evento detenido en `document`).
        // El bloqueo SILENCIOSO era indistinguible de una app rota: reportado
        // 2026-08-23 ("no puedo seleccionar Proveedor, no se sombrea") — el
        // usuario habia dejado el modo diseno prendido y los clicks del rail
        // se los comia esta funcion sin decir nada. Se conserva el bloqueo
        // (es lo que se pidio: no perder el trabajo por navegar sin querer)
        // y se le agrega ACUSE DE RECIBO: un cartelito junto al cursor que
        // dice por que no paso nada y como salir. Ver arquitectura.md #181.
        win.__disenoClickBlocker = function(e) {
            if (!disenoActivo()) return;
            if (esUIPropiaDeDiseno(e.target)) return;
            e.preventDefault();
            e.stopPropagation();
            avisarBloqueo(e.clientX, e.clientY);
        };
        win.addEventListener('scroll', win.__disenoScrollHandler, true);
        win.addEventListener('resize', win.__disenoResizeHandler);
        win.addEventListener('keydown', win.__disenoKeydownHandler);
        doc.addEventListener('click', win.__disenoClickBlocker, true);

        win.__disenoPollInterval = win.setInterval(sync, 150);
        sync();

    })();
    </script>
    """
