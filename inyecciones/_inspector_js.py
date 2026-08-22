"""inyecciones._inspector_js - el JS del inspector de elementos.

Blob de ~1.380 lineas que estaba embebido como un unico components.html
DENTRO de inject_element_inspector, seguido de una cadena de nueve
.replace() encadenados en UNA sola linea. Se saco el 2026-08-08: la
funcion era la mas grande del repo (1.415 lineas) y de eso, el 98% era
este string.

Lleva PLACEHOLDERS `__MAPA_*__` que el llamador sustituye por los mapas
JSON que arma _mapas_desarrollador(). No es un f-string a proposito: el
JS esta lleno de llaves y escaparlas todas seria ilegible.

NO CONVERTIR A RAW STRING. El JS trae regex escritos como \\( y \\s
dentro de un string NORMAL, donde el \\\\ colapsa a uno solo, que es
lo que espera el motor de regex del navegador. En un raw string
sobreviven duplicados y el navegador tira "Invalid regular expression:
Unterminated group" — con el inspector muerto entero. Paso exactamente
eso al extraer este modulo; ver arquitectura.md #56.

Ver el docstring de inspector.py para que hace el inspector y como se
activa (?debug=1 o Alt+I).
"""

JS = """
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;

        win.__inspectorMapaCodigo  = __MAPA_CODIGO__;
        win.__inspectorMapaEstilos = __MAPA_ESTILOS__;
        win.__inspectorMapaSnippets = __MAPA_SNIPPETS__;
        win.__inspectorMapaFuncion = __MAPA_FUNCION__;
        win.__inspectorMapaRefs    = __MAPA_REFS__;
        win.__inspectorMapaTexto     = __MAPA_TEXTO__;
        win.__inspectorMapaConstruido = __MAPA_CONSTRUIDO__;
        win.__inspectorMapaPrefijos  = __MAPA_PREFIJOS__;
        win.__inspectorSS            = __MAPA_SS__;

        // Fallback por PREFIJO para keys dinamicas. Muchas keys de esta app se
        // arman con f-string (chartcard_{slug}, atajo_{reporte}_{ca}, ...), asi
        // que su nombre EXACTO no existe en el codigo fuente y los mapas por
        // key no la encuentran. Python indexa el prefijo estatico de esas
        // keys (ver _mapas_desarrollador) y aca se resuelve al prefijo MAS
        // LARGO que sea prefijo de la key: entre "compras_g_" y
        // "compras_g_fam_time_" gana el segundo, que apunta a la linea real.
        //
        // El mapa suele tener pocas decenas de entradas, asi que el barrido
        // lineal es mas barato que trocear la key y probar cada corte.
        function registroPorPrefijo(key) {
            if (!key) return null;
            var m = win.__inspectorMapaPrefijos, mejor = null;
            for (var p in m) {
                if (key.indexOf(p) === 0 && (mejor === null || p.length > mejor.length)) {
                    mejor = p;
                }
            }
            return mejor === null ? null : m[mejor];
        }
        // Devuelve el campo del registro por prefijo, o el vacio que toque.
        function porPrefijo(key, campo, vacio) {
            var reg = registroPorPrefijo(key);
            return (reg && reg[campo]) ? reg[campo] : vacio;
        }

        function buscarConstruido(key) {
            if (!key) return '';
            return win.__inspectorMapaConstruido[key] || '';
        }

        function buscarPorTexto(txt) {
            // Busca el innerText normalizado en el indice de literales st.XXX("...").
            // Devuelve "archivo:linea" o ''.
            if (!txt) return '';
            var norm = txt.toLowerCase().replace(/\\s+/g, ' ').trim();
            if (!norm || norm.length < 2 || norm.length > 100) return '';
            // Quitar iconos Material (palabras de una sola raiz al final tipo "expand_more")
            norm = norm.replace(/\\s+(expand_more|expand_less|arrow_drop_down|check|close)$/g, '');
            var m = win.__inspectorMapaTexto;
            if (m[norm]) return m[norm];
            // Match parcial: si el innerText contiene el literal como prefijo/substring.
            // Barato porque el indice suele tener <300 entradas.
            for (var k in m) {
                if (norm.indexOf(k) !== -1) return m[k];
            }
            return '';
        }

        // Los cuatro caen al fallback por prefijo cuando la key exacta no
        // esta (key dinamica). Ojo: el registro por prefijo usa "snippet" en
        // singular, mientras el mapa por key es "Snippets".
        function buscarCodigo(key) {
            if (!key) return '';
            return win.__inspectorMapaCodigo[key] || porPrefijo(key, 'codigo', '');
        }
        function buscarSnippet(key) {
            if (!key) return '';
            return win.__inspectorMapaSnippets[key] || porPrefijo(key, 'snippet', '');
        }
        function buscarFuncion(key) {
            if (!key) return '';
            return win.__inspectorMapaFuncion[key] || porPrefijo(key, 'funcion', '');
        }
        function buscarRefs(key) {
            if (!key) return [];
            var r = win.__inspectorMapaRefs[key];
            return (r && r.length) ? r : porPrefijo(key, 'refs', []);
        }
        function buscarSS(key) {
            if (!key) return '';
            var ss = win.__inspectorSS;
            return ss.hasOwnProperty(key) ? ss[key] : '';
        }
        function buscarEstilos(key) {
            if (!key) return [];
            var m = win.__inspectorMapaEstilos;
            var vistos = {};
            var res = [];
            // match exacto + prefijos progresivos (vista_cards_kpi_1 -> vista_cards_kpi -> vista_cards -> vista)
            var partes = key.split('_');
            for (var i = partes.length; i >= 1; i--) {
                var p = partes.slice(0, i).join('_');
                var arr = m[p];
                if (arr) {
                    for (var j = 0; j < arr.length; j++) {
                        if (!vistos[arr[j]]) { vistos[arr[j]] = 1; res.push(arr[j]); }
                    }
                }
            }
            return res;
        }
        function keyDeElemento(el) {
            if (!el || !el.className || !el.className.toString) return '';
            var m = /st-key-([A-Za-z0-9_]+)/.exec(el.className.toString());
            return m ? m[1] : '';
        }
        function contenedorConKey(el) {
            var cur = el;
            while (cur && cur !== doc.body) {
                var k = keyDeElemento(cur);
                if (k) return { el: cur, key: k };
                cur = cur.parentElement;
            }
            return null;
        }
        function padreYHermanos(el) {
            var mio = contenedorConKey(el);
            if (!mio) return { padre: '', hermanos: [] };
            var arriba = contenedorConKey(mio.el.parentElement);
            if (!arriba) return { padre: '', hermanos: [] };
            var hermanos = [];
            var candidatos = arriba.el.querySelectorAll('[class*="st-key-"]');
            for (var i = 0; i < candidatos.length; i++) {
                // solo hermanos DIRECTOS de nuestro contenedor, no descendientes
                if (candidatos[i].parentElement !== arriba.el) continue;
                var k = keyDeElemento(candidatos[i]);
                if (k && k !== mio.key) hermanos.push(k);
            }
            var mostrados = hermanos.slice(0, 12);
            if (hermanos.length > 12) mostrados.push('(+' + (hermanos.length - 12) + ' mas)');
            return { padre: arriba.key, hermanos: mostrados };
        }
        function medirElemento(el) {
            if (!el || !el.getBoundingClientRect) return null;
            var r = el.getBoundingClientRect();
            var cs = win.getComputedStyle(el);
            var pick = function(p) { return (cs.getPropertyValue(p) || '').trim(); };
            // Coords absolutas (viewport). En cliente los top/left CSS pueden mentir
            // por transform/position del padre; getBoundingClientRect es la verdad.
            var coords = 'top=' + Math.round(r.top) + ' left=' + Math.round(r.left) +
                         ' right=' + Math.round(r.right) + ' bottom=' + Math.round(r.bottom);
            var vw = win.innerWidth, vh = win.innerHeight;
            var visible = (r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw);
            var est = {
                'font-size'   : pick('font-size'),
                'color'       : pick('color'),
                'background'  : pick('background-color'),
                'padding'     : pick('padding'),
                'margin'      : pick('margin'),
                'border-radius': pick('border-radius')
            };
            // Desglose de margin por lado cuando cualquiera sea no cero (incluye
            // negativos). El shorthand 'margin' se filtra despues por ser '0px' y
            // dejaba invisibles los margenes negativos como margin-top:-110px, que
            // son la explicacion habitual de "por que este elemento se pega arriba".
            var lados = ['margin-top','margin-right','margin-bottom','margin-left'];
            var hayMargen = false;
            for (var li = 0; li < lados.length; li++) {
                var v = pick(lados[li]);
                if (v && v !== '0px') hayMargen = true;
            }
            if (hayMargen) {
                for (var lj = 0; lj < lados.length; lj++) est[lados[lj]] = pick(lados[lj]);
            }
            // Position/top/left/transform: si el elemento esta posicionado o
            // trasladado explicitamente, importan para explicar donde termino.
            var pos = pick('position');
            if (pos && pos !== 'static') {
                est['position'] = pos;
                var offs = ['top','right','bottom','left'];
                for (var oi = 0; oi < offs.length; oi++) {
                    var ov = pick(offs[oi]);
                    if (ov && ov !== 'auto' && ov !== '0px') est[offs[oi]] = ov;
                }
            }
            var tr = pick('transform');
            if (tr && tr !== 'none') est['transform'] = tr;
            return {
                tamano: Math.round(r.width) + ' x ' + Math.round(r.height) + ' px',
                coords: coords + (visible ? '' : ' (FUERA DEL VIEWPORT)'),
                estilos: est
            };
        }
        function archivoDeSelector(selectorText) {
            // Extrae la key mas larga del selector y la mapea a estilos/*.py.
            // Devuelve string o '' si no se pudo atribuir.
            var m = /st-key-([A-Za-z0-9_]+)/g;
            var mejor = '', match;
            while ((match = m.exec(selectorText)) !== null) {
                var k = match[1].replace(/_+$/, '');
                if (k.length > mejor.length) mejor = k;
            }
            if (!mejor) return '';
            var map = win.__inspectorMapaEstilos;
            var partes = mejor.split('_');
            for (var i = partes.length; i >= 1; i--) {
                var p = partes.slice(0, i).join('_');
                if (map[p]) return map[p].join('+');
            }
            return '';
        }
        function cadenaKeys(el) {
            // recorre desde el elemento hasta el body coleccionando todos los st-key-*
            // asi se ve exactamente el anidamiento de contenedores keyed en el DOM real.
            var out = [];
            var cur = el;
            while (cur && cur !== doc.body && out.length < 12) {
                var k = keyDeElemento(cur);
                if (k && out.indexOf(k) === -1) out.push(k);
                cur = cur.parentElement;
            }
            return out;
        }
        function cadenaTestids(el) {
            var out = [];
            var cur = el;
            while (cur && cur !== doc.body && out.length < 8) {
                var t = cur.getAttribute && cur.getAttribute('data-testid');
                if (t) out.push(t);
                cur = cur.parentElement;
            }
            return out;
        }
        // ── Anclas de estilo: cual es la del PROPIO widget y cuanto pesa
        // cada ancestro. Nacio de un bug real (arquitectura.md regla #90):
        // para "subir un poco este toggle" se toco el margin del ancestro
        // que el inspector mostraba a mano, y ese ancestro envolvia las 10
        // vistas del rail — movio el reporte entero. La cadena st-key ya
        // estaba en el tooltip, pero como texto plano: no distinguia el
        // ancla propia de los ancestros ni decia que habia dentro de cada
        // uno. Estas dos funciones responden justo eso.
        function anclaPropia(el) {
            // El st-key MAS CERCANO que envuelve SOLO a este widget. Todo
            // st.X(key="K") emite st-key-K en su element container, asi que
            // casi siempre existe — y es el selector correcto para estilar
            // el widget sin tocar a nadie mas.
            var cur = el;
            while (cur && cur !== doc.body) {
                var k = keyDeElemento(cur);
                if (k) {
                    var td = cur.getAttribute && cur.getAttribute('data-testid');
                    // stElementContainer = envoltorio de UN widget suelto.
                    // stVerticalBlock = un st.container, puede traer varios.
                    return { key: k, soloWidget: (td === 'stElementContainer') };
                }
                cur = cur.parentElement;
            }
            return null;
        }
        function pesoAncestros(el) {
            // Por cada contenedor keyed de la cadena: cuantos widgets vivos
            // tiene adentro. Un ancestro con decenas de hijos es una senal
            // de "no me toques el margen para mover una sola cosa".
            var out = [];
            var cur = el, primero = true;
            while (cur && cur !== doc.body && out.length < 6) {
                var k = keyDeElemento(cur);
                if (k) {
                    var n = 0;
                    try { n = cur.querySelectorAll('[data-testid="stElementContainer"]').length; } catch(_) {}
                    out.push({ key: k, widgets: n, propio: primero });
                    primero = false;
                }
                cur = cur.parentElement;
            }
            return out;
        }
        function selectoresCompartidos(el) {
            // Reglas de estilos/ que matchean `el` con un selector WILDCARD
            // por prefijo ([class*="st-key-pre_"]) en vez de su key exacta.
            // Editar esa regla toca TODOS los contenedores con ese prefijo
            // — en este proyecto, tipicamente los 5 reportes que comparten
            // ajuste_graf_card_izq_*. Mismo recorrido de styleSheets que
            // reglasQueMatchean (no hay indice global de reglas).
            if (!el || !el.matches) return [];
            var out = [], vistos = {};
            var sheets = doc.styleSheets;
            for (var s = 0; s < sheets.length; s++) {
                var rules = null;
                try { rules = sheets[s].cssRules; } catch(e) { continue; }
                if (!rules) continue;
                for (var r = 0; r < rules.length && out.length < 4; r++) {
                    var rule = rules[r];
                    if (!rule.selectorText || !rule.style) continue;
                    if (rule.selectorText.indexOf('[class*="st-key-') === -1) continue;
                    var sels = rule.selectorText.split(',');
                    for (var si = 0; si < sels.length; si++) {
                        var st = sels[si].trim();
                        var m = /\\[class\\*="st-key-([A-Za-z0-9_]+)"\\]/.exec(st);
                        if (!m) continue;
                        var ok = false;
                        try { ok = el.matches(st); } catch(_) { continue; }
                        if (!ok || vistos[st]) continue;
                        // NO se filtra por "cuantos matchean ahora": la app
                        // renderiza UN reporte por vez, asi que un wildcard
                        // que cubre los 5 reportes igual devuelve 1 en el DOM
                        // vivo. La senal es el selector en si — esta escrito
                        // para una FAMILIA (prefijo), no para esta key.
                        var cuantos = 0;
                        try { cuantos = doc.querySelectorAll('[class*="st-key-' + m[1] + '"]').length; } catch(_) {}
                        vistos[st] = 1;
                        out.push({ sel: (st.length > 120 ? st.slice(0, 117) + '...' : st),
                                   archivo: archivoDeSelector(rule.selectorText) || '',
                                   prefijo: m[1], captura: cuantos });
                        if (out.length >= 4) break;
                    }
                }
            }
            return out;
        }
        function clasesElemento(el) {
            if (!el || !el.classList) return [];
            var arr = [];
            for (var i = 0; i < el.classList.length; i++) arr.push(el.classList[i]);
            return arr;
        }
        function reglasQueMatchean(el) {
            // Devuelve {archivo -> [{sel, props}]} de reglas en estilos/*.py que matchean el elemento.
            if (!el || !el.matches) return {};
            var acumulado = {};
            var sheets = doc.styleSheets;
            for (var s = 0; s < sheets.length; s++) {
                var rules = null;
                try { rules = sheets[s].cssRules; } catch(e) { continue; }
                if (!rules) continue;
                for (var r = 0; r < rules.length; r++) {
                    var rule = rules[r];
                    if (!rule.selectorText || !rule.style) continue;
                    var sels = rule.selectorText.split(',');
                    var matcheantes = [];
                    for (var si = 0; si < sels.length; si++) {
                        var st = sels[si].trim();
                        try { if (el.matches(st)) matcheantes.push(st); } catch(_){}
                    }
                    if (!matcheantes.length) continue;
                    var arch = archivoDeSelector(rule.selectorText);
                    if (!arch) continue;
                    acumulado[arch] = acumulado[arch] || [];
                    var props = rule.style.cssText || '';
                    if (props.length > 300) props = props.slice(0, 297) + '...';
                    for (var k = 0; k < matcheantes.length; k++) {
                        var sn = matcheantes[k];
                        if (sn.length > 200) sn = sn.slice(0, 197) + '...';
                        var yaExiste = false;
                        for (var q = 0; q < acumulado[arch].length; q++) {
                            if (acumulado[arch][q].sel === sn) { yaExiste = true; break; }
                        }
                        if (!yaExiste) acumulado[arch].push({sel: sn, props: props});
                    }
                }
            }
            return acumulado;
        }
        function pseudoInfo(el, cual) {
            // Estilos COMPUTADOS de ::before / ::after. Clave para bandas del
            // proyecto (.st-key-fila_ajuste_top::before, .stApp::after) que se
            // pintan enteras en un pseudo: el.matches() no puede matchear un
            // selector de pseudo, asi que reglasQueMatchean() nunca las ve. Aca
            // leemos el resultado ya resuelto. Devuelve string formateado o ''.
            if (!el) return '';
            var cs;
            try { cs = win.getComputedStyle(el, cual); } catch(_) { return ''; }
            if (!cs) return '';
            var content = (cs.getPropertyValue('content') || '').trim();
            // Pseudo ausente => content 'none' (o 'normal'). content:"" existente
            // computa como '""' (con comillas): truthy y != none/normal.
            if (!content || content === 'none' || content === 'normal') return '';
            var interesantes = ['content','position','top','right','bottom','left',
                'width','height','background-color','border-top','border-bottom',
                'box-shadow','transform','z-index','margin','padding'];
            var defaults = {
                'position':'static','top':'auto','right':'auto','bottom':'auto',
                'left':'auto','width':'auto','height':'auto',
                'background-color':'rgba(0, 0, 0, 0)','box-shadow':'none',
                'transform':'none','z-index':'auto','margin':'0px','padding':'0px'
            };
            var partes = [];
            for (var i = 0; i < interesantes.length; i++) {
                var k = interesantes[i];
                var v = (cs.getPropertyValue(k) || '').trim();
                if (!v) continue;
                if (k === 'content') { partes.push('content=' + v); continue; }
                if (defaults.hasOwnProperty(k) && v === defaults[k]) continue;
                if (v === '0px' || v === 'none' || v === 'auto') continue;
                if ((k === 'border-top' || k === 'border-bottom') && v.indexOf('0px') === 0) continue;
                partes.push(k + '=' + v);
            }
            return partes.join(' | ');
        }

        function nombresVarsRoot() {
            // Nombres de todas las custom props definidas en reglas :root
            // (estilos/_00_base.py). Se escanea una vez y se cachea en win:
            // los NOMBRES son estables entre reruns (los valores se resuelven
            // frescos cada vez, por si cambian con tema/breakpoint).
            if (win.__inspectorVarsRoot) return win.__inspectorVarsRoot;
            var nombres = {};
            var sheets = doc.styleSheets;
            for (var s = 0; s < sheets.length; s++) {
                var rules = null;
                try { rules = sheets[s].cssRules; } catch(e) { continue; }
                if (!rules) continue;
                for (var r = 0; r < rules.length; r++) {
                    var rule = rules[r];
                    if (!rule.selectorText || !rule.style) continue;
                    if (rule.selectorText.indexOf(':root') === -1) continue;
                    for (var pi = 0; pi < rule.style.length; pi++) {
                        var prop = rule.style[pi];
                        if (prop.indexOf('--') === 0) nombres[prop] = 1;
                    }
                }
            }
            win.__inspectorVarsRoot = Object.keys(nombres);
            return win.__inspectorVarsRoot;
        }

        function varsEnTexto(el, texto) {
            // Extrae var(--x) del texto CSS AUTORADO (cssText de las reglas que
            // matchean, que preserva el var() sin resolver) y devuelve cada una
            // con su valor numerico ACTUAL, resuelto contra el elemento (las
            // custom props cascadean, asi que el valor efectivo puede diferir
            // del :root si un ancestro la redefine). Responde a: "usa
            // var(--cab-altura) pero no se cuanto vale ahora".
            if (!texto) return [];
            var re = /var\\(\\s*(--[A-Za-z0-9_-]+)/g, m, vistos = {}, out = [];
            var base = el || doc.documentElement;
            var cs = win.getComputedStyle(base);
            while ((m = re.exec(texto)) !== null) {
                var nombre = m[1];
                if (vistos[nombre]) continue;
                vistos[nombre] = 1;
                var val = (cs.getPropertyValue(nombre) || '').trim();
                out.push(nombre + ' = ' + (val || '(sin valor)'));
            }
            return out;
        }

        function reporteActivoDOM() {
            // Reporte activo REAL, leido del marker que app.py inyecta
            // (.st-key-app_reporte_<slug>). Mas fiable que el query ?reporte=,
            // que suele faltar cuando entras con solo ?debug=1. El slug importa
            // porque el CSS scopeado por :has(.st-key-app_reporte_*) depende de el.
            var nodos = doc.querySelectorAll('[class*="st-key-app_reporte_"]');
            for (var i = 0; i < nodos.length; i++) {
                var cn = nodos[i].className;
                if (!cn || !cn.toString) continue;
                var m = /st-key-app_reporte_([A-Za-z0-9_]+)/.exec(cn.toString());
                if (m) return m[1];
            }
            return '';
        }

        function analizarConflictos(el) {
            if (!el || !el.matches) return [];
            var propsPorRegla = {}; // prop -> [{val, imp, sel, archivo}]
            var sheets = doc.styleSheets;
            for (var s = 0; s < sheets.length; s++) {
                var rules = null;
                try { rules = sheets[s].cssRules; } catch(e) { continue; } // cross-origin
                if (!rules) continue;
                for (var r = 0; r < rules.length; r++) {
                    var rule = rules[r];
                    if (!rule.selectorText || !rule.style) continue;
                    // el.matches falla con selectores raros; try/catch por selector individual
                    var sels = rule.selectorText.split(',');
                    var matched = false;
                    for (var si = 0; si < sels.length; si++) {
                        try { if (el.matches(sels[si].trim())) { matched = true; break; } } catch(_){}
                    }
                    if (!matched) continue;
                    var arch = archivoDeSelector(rule.selectorText);
                    for (var pi = 0; pi < rule.style.length; pi++) {
                        var prop = rule.style[pi];
                        var val  = rule.style.getPropertyValue(prop).trim();
                        var imp  = rule.style.getPropertyPriority(prop) === 'important';
                        propsPorRegla[prop] = propsPorRegla[prop] || [];
                        propsPorRegla[prop].push({ val: val, imp: imp, sel: rule.selectorText.slice(0, 80), archivo: arch });
                    }
                }
            }
            var conflictos = [];
            for (var p in propsPorRegla) {
                var list = propsPorRegla[p];
                if (list.length < 2) continue;
                // deduplico valores identicos - si todas las reglas ponen el mismo valor no es conflicto real
                var valoresUnicos = {};
                for (var k = 0; k < list.length; k++) valoresUnicos[list[k].val + '|' + list[k].imp] = 1;
                if (Object.keys(valoresUnicos).length < 2) continue;
                var ganador = list[list.length - 1]; // ultima que matcheo suele ganar (aprox)
                conflictos.push({
                    prop: p, cantidad: list.length,
                    ganador: ganador,
                    otros: list.slice(0, -1)
                });
            }
            return conflictos.slice(0, 8); // limitar ruido
        }
        function contextoPagina() {
            try {
                var u = new URL(win.location.href);
                // Fuente de verdad: el marker del DOM (app.py). El query solo se
                // usa como respaldo/etiqueta si el DOM no lo trae.
                var domRep = reporteActivoDOM();
                var urlRep = u.searchParams.get('reporte') || u.searchParams.get('r') || '';
                var reporte;
                if (domRep) {
                    reporte = domRep + ' (slug DOM' + (urlRep ? '' : '; no en URL') + ')';
                } else {
                    reporte = urlRep || '(desconocido)';
                }
                var w = win.innerWidth || 0;
                var modo = w < 640 ? 'movil' : (w < 1024 ? 'tablet' : 'desktop');
                return {
                    url: u.pathname + (u.search || ''),
                    reporte: reporte,
                    viewport: w + ' px (' + modo + ')'
                };
            } catch(e) { return { url: '?', reporte: '?', viewport: '?' }; }
        }
        function formatearConflictos(conf) {
            if (!conf || !conf.length) return [];
            var out = ['Conflictos CSS (mismo elemento, mismas propiedades):'];
            for (var i = 0; i < conf.length; i++) {
                var c = conf[i];
                var linea = '  ' + c.prop + ' - ' + c.cantidad + ' reglas | gana: ' +
                            c.ganador.val + (c.ganador.imp ? ' !important' : '') +
                            (c.ganador.archivo ? ' (' + c.ganador.archivo + ')' : '');
                out.push(linea);
                for (var j = 0; j < c.otros.length && j < 2; j++) {
                    var o = c.otros[j];
                    out.push('     pierde: ' + o.val + (o.imp ? ' !important' : '') +
                             (o.archivo ? ' (' + o.archivo + ')' : '') +
                             ' | sel: ' + o.sel);
                }
            }
            return out;
        }
        function layoutPadre(el) {
            var cont = contenedorConKey(el);
            if (!cont) return '';
            var padre = cont.el.parentElement;
            if (!padre) return '';
            var cs = win.getComputedStyle(padre);
            var d = cs.display || '';
            var info = 'display=' + d;
            if (d.indexOf('flex') !== -1) {
                info += ' | flex-direction=' + (cs.flexDirection || '');
                info += ' | gap=' + (cs.gap || '0px');
                info += ' | align-items=' + (cs.alignItems || '');
            }
            if (d.indexOf('grid') !== -1) {
                info += ' | grid-template-columns=' + (cs.gridTemplateColumns || '');
                info += ' | gap=' + (cs.gap || '0px');
            }
            return info;
        }
        function estilosCajaDe(nodo) {
            // Devuelve string tipo "margin-top=-110px | position=absolute | transform=..."
            // solo con las propiedades que EXPLICAN posicion/tamano y no son default.
            // Usado por boxPadre (DOM directo) y boxPadreKey (ancestro keyed).
            if (!nodo) return '';
            var cs = win.getComputedStyle(nodo);
            var partes = [];
            var lados = ['margin-top','margin-right','margin-bottom','margin-left',
                         'padding-top','padding-right','padding-bottom','padding-left'];
            for (var i = 0; i < lados.length; i++) {
                var v = (cs.getPropertyValue(lados[i]) || '').trim();
                if (v && v !== '0px') partes.push(lados[i] + '=' + v);
            }
            var pos = (cs.getPropertyValue('position') || '').trim();
            if (pos && pos !== 'static') {
                partes.push('position=' + pos);
                var offs = ['top','right','bottom','left'];
                for (var oi = 0; oi < offs.length; oi++) {
                    var ov = (cs.getPropertyValue(offs[oi]) || '').trim();
                    if (ov && ov !== 'auto' && ov !== '0px') partes.push(offs[oi] + '=' + ov);
                }
            }
            var tr = (cs.getPropertyValue('transform') || '').trim();
            if (tr && tr !== 'none') partes.push('transform=' + tr);
            var ov2 = (cs.getPropertyValue('overflow') || '').trim();
            if (ov2 && ov2 !== 'visible') partes.push('overflow=' + ov2);
            var z = (cs.getPropertyValue('z-index') || '').trim();
            if (z && z !== 'auto' && z !== '0') partes.push('z-index=' + z);
            return partes.join(' | ');
        }
        function boxPadre(el) {
            var cont = contenedorConKey(el);
            if (!cont) return '';
            return estilosCajaDe(cont.el.parentElement);
        }
        function boxPadreKey(el) {
            // Estilos computados del ANCESTRO KEYED (el que aparece como "Padre:
            // st-key-X"), no del parentElement DOM directo. Reglas en estilos/
            // que aplican margin/position al wrapper viven aca: si no lo dumpeamos,
            // el "por que se pega arriba" queda invisible.
            var mio = contenedorConKey(el);
            if (!mio) return '';
            var arriba = contenedorConKey(mio.el.parentElement);
            if (!arriba) return '';
            return estilosCajaDe(arriba.el);
        }
        function bloqueParaIA(etiqueta, key, ctx, medidas, pagina, conflictos, matcheantes, extras2) {
            var lines = ['--- copiar para IA ---'];
            lines.push('Widget key: ' + (key || '(sin key)'));
            if (ctx.codigo)   lines.push('Declarado en: ' + ctx.codigo);
            if (ctx.construido) lines.push('Contenedor construido por: ' + ctx.construido);
            if (ctx.origenTexto && ctx.origenTexto !== ctx.codigo)
                              lines.push('Origen del texto: ' + ctx.origenTexto);
            if (ctx.funcion)  lines.push('Funcion: ' + ctx.funcion);
            if (ctx.refs && ctx.refs.length) lines.push('Referencias (' + ctx.refs.length + '): ' + ctx.refs.join(', '));
            if (ctx.ss !== undefined && ctx.ss !== '')  lines.push('session_state[' + key + '] = ' + ctx.ss);
            if (ctx.estilos && ctx.estilos.length) lines.push('Estilos: ' + ctx.estilos.join(', '));
            if (ctx.padre)    lines.push('Padre: st-key-' + ctx.padre);
            if (ctx.hermanos && ctx.hermanos.length) lines.push('Hermanos: ' + ctx.hermanos.join(', '));
            if (medidas) {
                lines.push('Tamano actual: ' + medidas.tamano);
                if (medidas.coords) lines.push('Coords viewport: ' + medidas.coords);
                var e = medidas.estilos, partes = [];
                for (var p in e) { if (e[p] && e[p] !== 'none' && e[p] !== '0px') partes.push(p + '=' + e[p]); }
                if (partes.length) lines.push('Estilos computados: ' + partes.join(' | '));
            }
            if (pagina) {
                lines.push('URL: ' + pagina.url);
                lines.push('Reporte activo: ' + pagina.reporte);
                lines.push('Viewport: ' + pagina.viewport);
            }
            if (extras2) {
                // ANCLA PROPIA primero y con nombre explicito: es el selector
                // con el que se estila ESTE widget sin tocar a nadie mas.
                // Va antes de la cadena a proposito — leer la cadena y elegir
                // un ancestro fue justo el error de la regla #90.
                if (extras2.ancla) {
                    lines.push('ANCLA PROPIA (estila SOLO este widget): div[class*="st-key-'
                               + extras2.ancla.key + '"]'
                               + (extras2.ancla.soloWidget ? '' : '  <- ojo: es un container, puede traer hermanos'));
                }
                if (extras2.pesos && extras2.pesos.length) {
                    // Solo los ANCESTROS: el ancla propia ya se reporto arriba,
                    // y contar "widgets adentro" de la propia caja del widget
                    // da 0, que se lee como si estuviera vacia.
                    var _pz = [];
                    for (var pi = 0; pi < extras2.pesos.length; pi++) {
                        var _p = extras2.pesos[pi];
                        if (_p.propio) continue;
                        _pz.push('st-key-' + _p.key + ' (' + _p.widgets + ' widget'
                                 + (_p.widgets === 1 ? '' : 's') + ' adentro)');
                    }
                    if (_pz.length) {
                        lines.push('Contenedores que lo ENVUELVEN: ' + _pz.join(' > '));
                        lines.push('  ^ tocar el margen/padding de uno de estos mueve todo su contenido, no solo este widget');
                    }
                }
                if (extras2.compartidos && extras2.compartidos.length) {
                    lines.push('AVISO - el contenedor que lo envuelve lo estilan reglas WILDCARD (por familia, no por su key):');
                    for (var ci = 0; ci < extras2.compartidos.length; ci++) {
                        var _c = extras2.compartidos[ci];
                        lines.push('  ' + _c.sel + (_c.archivo ? '  [' + _c.archivo + ']' : ''));
                        lines.push('    -> familia "st-key-' + _c.prefijo
                                   + '*"; editar esa regla afecta a TODOS sus miembros'
                                   + ' (ahora se renderiza ' + _c.captura + ')');
                    }
                }
                if (extras2.keysCad && extras2.keysCad.length)
                    lines.push('Cadena de contenedores st-key (elemento -> raiz): ' + extras2.keysCad.join(' > '));
                if (extras2.testids && extras2.testids.length)
                    lines.push('Cadena de data-testid (elemento -> raiz): ' + extras2.testids.join(' > '));
                if (extras2.clases && extras2.clases.length)
                    lines.push('Clases del elemento hovereado (NO de contenedores): ' + extras2.clases.join(' '));
                if (extras2.layoutPadre)
                    lines.push('Layout del padre: ' + extras2.layoutPadre);
                if (extras2.boxPadre)
                    lines.push('Box del padre (DOM directo): ' + extras2.boxPadre);
                if (extras2.boxPadreKey)
                    lines.push('Estilos computados del padre (st-key): ' + extras2.boxPadreKey);
                if (extras2.pseudoBefore)
                    lines.push('Pseudo ::before (computado): { ' + extras2.pseudoBefore + ' }');
                if (extras2.pseudoAfter)
                    lines.push('Pseudo ::after (computado): { ' + extras2.pseudoAfter + ' }');
                if (extras2.varsCSS && extras2.varsCSS.length)
                    lines.push('Variables CSS usadas (valor actual): ' + extras2.varsCSS.join(' | '));
            }
            function _volcarMatcheantes(header, dict) {
                if (!dict) return;
                var archs = Object.keys(dict);
                if (!archs.length) return;
                lines.push(header);
                for (var a = 0; a < archs.length; a++) {
                    var reglas = dict[archs[a]];
                    lines.push('  ' + archs[a] + ' (' + reglas.length + ' regla' + (reglas.length > 1 ? 's' : '') + '):');
                    for (var si2 = 0; si2 < reglas.length && si2 < 4; si2++) {
                        lines.push('     ' + reglas[si2].sel);
                        if (reglas[si2].props) lines.push('       { ' + reglas[si2].props + ' }');
                    }
                    if (reglas.length > 4) lines.push('     ...(' + (reglas.length - 4) + ' mas)');
                }
            }
            _volcarMatcheantes('Reglas de estilos/ que matchean este elemento:', matcheantes);
            if (extras2 && extras2.matcheantesPadreKey) {
                var _lbl = extras2.padreKeyNombre
                    ? ('Reglas de estilos/ que matchean el padre (st-key-' + extras2.padreKeyNombre + '):')
                    : 'Reglas de estilos/ que matchean el padre (st-key):';
                _volcarMatcheantes(_lbl, extras2.matcheantesPadreKey);
            }
            var flat = formatearConflictos(conflictos);
            for (var i = 0; i < flat.length; i++) lines.push(flat[i]);
            if (ctx.snippet) lines.push('Codigo Python (contexto):\\n' + ctx.snippet);
            if (etiqueta) lines.push('Detalle:\\n' + etiqueta);
            return lines.join('\\n');
        }

        // ── Migas de pan clicables (regla #155) ─────────────────────────
        // "Cadena de contenedores st-key (elemento -> raiz)" ya vivia en el
        // texto plano (bloqueParaIA de arriba) pero como texto: para saltar
        // a un ancestro habia que ubicarlo A OJO en la pantalla y clic-
        // derecho ahi. Reusa la MISMA lista (`keysCad`, mismo orden) como
        // botones de verdad.
        //
        // saltarAAncestro no dispara un mousemove real ni usa dispatchEvent:
        // el handler solo lee target/clientX/clientY del objeto que recibe
        // (ver mousemove handler mas abajo), asi que un objeto armado a mano
        // alcanza -- mismo truco liviano que __inspectorContextMenuHandler ya
        // usa para "recalcular en la posicion actual" reusando el handler
        // directo en vez de simular un evento de DOM real.
        function saltarAAncestro(key) {
            var el = doc.querySelector('.st-key-' + key);
            if (!el || !win.__inspectorMouseMoveHandler) return;
            var r = el.getBoundingClientRect();
            var cx = r.left + Math.min(12, r.width / 2);
            var cy = r.top + Math.min(12, r.height / 2);
            // Soltar primero: el handler ignora todo (`return` temprano) si
            // sigue fijado, sea a este elemento o a otro.
            if (win.__inspectorPinned && win.__inspectorTogglePin) win.__inspectorTogglePin(true);
            win.__inspectorMouseMoveHandler({ target: el, clientX: cx, clientY: cy });
            // Re-fijar sobre el ancestro nuevo: sin esto, el proximo
            // mousemove real (el cursor sigue donde estaba, no sobre el
            // ancestro) pisaria el salto al instante.
            if (win.__inspectorTogglePin) win.__inspectorTogglePin();
        }

        function pintarMigas(cadena) {
            var box = doc.getElementById('el-inspector-migas');
            if (!box) return;
            box.innerHTML = '';
            if (!cadena || cadena.length < 2) { box.style.display = 'none'; return; }
            box.style.display = 'flex';
            cadena.forEach(function(k, i) {
                if (i > 0) {
                    var sep = doc.createElement('span');
                    sep.textContent = '\\u203a';
                    sep.style.cssText = 'color:#54546a;flex-shrink:0;padding:0 1px;font:11px sans-serif';
                    box.appendChild(sep);
                }
                var esActual = (i === 0);
                var b = doc.createElement('button');
                b.textContent = k;
                b.title = esActual ? 'este elemento' : ('saltar a st-key-' + k);
                b.style.cssText = 'background:transparent;border:0;padding:2px 4px;'
                    + 'border-radius:3px;font:11px "Courier New",monospace;'
                    + 'cursor:' + (esActual ? 'default' : 'pointer') + ';'
                    + 'color:' + (esActual ? '#cfcfd6' : '#9385ec') + ';'
                    + 'white-space:nowrap;flex-shrink:0';
                if (!esActual) {
                    b.addEventListener('mouseenter', function() { b.style.background = '#2A2A35'; });
                    b.addEventListener('mouseleave', function() { b.style.background = 'transparent'; });
                    b.addEventListener('click', function(ev) {
                        ev.preventDefault(); ev.stopPropagation();
                        saltarAAncestro(k);
                    });
                }
                box.appendChild(b);
            });
        }

        function inspectorActivo() {
            return new URL(win.location.href).searchParams.get('debug') === '1';
        }

        function copiarTexto(texto, onOk, onFail) {
            var okDone = false;
            var mark = function() { if (!okDone) { okDone = true; onOk(); } };
            if (win.navigator.clipboard && win.navigator.clipboard.writeText && win.isSecureContext) {
                try {
                    win.navigator.clipboard.writeText(texto).then(mark, function(){ execFallback(); });
                    // navegadores viejos: el then puede no ejecutarse. Timeout 300ms => fallback.
                    setTimeout(function(){ if (!okDone) execFallback(); }, 300);
                    return;
                } catch(_) {}
            }
            execFallback();
            function execFallback() {
                if (okDone) return;
                var ta = doc.createElement('textarea');
                ta.value = texto;
                ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;opacity:0';
                doc.body.appendChild(ta);
                ta.focus(); ta.select();
                var okExec = false;
                try { okExec = doc.execCommand('copy'); } catch(_) {}
                doc.body.removeChild(ta);
                if (okExec) mark();
                else if (onFail) onFail();
            }
        }

        var tip = doc.getElementById('el-inspector-tip');
        if (!tip) {
            tip = doc.createElement('div');
            tip.id = 'el-inspector-tip';
            tip.style.cssText = [
                'position:fixed',
                // pointer-events:none en el contenedor: el cursor "atraviesa"
                // visualmente el tooltip, asi mousemove sigue apuntando al
                // elemento debajo y no se congela cuando la caja del tooltip
                // (que crecio mucho con los bloques del padre) engulle al
                // cursor. Los hijos que necesitan click (btnrow) reactivan
                // pointer-events:auto en su propio style inline.
                // Trade-off: se pierde scroll con la rueda dentro del tooltip,
                // pero el bloque completo ya se copia con la tecla C.
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
                'max-width:480px',
                'max-height:60vh',
                'overflow-y:auto',
                'overflow-x:hidden',
                'box-shadow:0 3px 12px rgba(0,0,0,0.5)'
            ].join(';');
            tip.innerHTML =
                '<div id="el-inspector-btnrow" style="position:sticky;top:-7px;background:#101014;padding:4px 0 6px;margin:-1px 0 6px;border-bottom:1px solid #3C3489;display:flex;gap:6px;z-index:1;pointer-events:auto">' +
                '  <button id="el-inspector-copiar" style="background:#3C3489;color:#fff;border:0;padding:5px 10px;border-radius:4px;cursor:pointer;font:600 11px/1 sans-serif">Copiar para IA</button>' +
                '  <button id="el-inspector-pin" title="Clic derecho sobre un elemento fija Y copia (este boton solo fija)" style="background:#2A2A35;color:#fff;border:0;padding:5px 10px;border-radius:4px;cursor:pointer;font:600 11px/1 sans-serif">\\uD83D\\uDCCC Fijar</button>' +
                '  <span id="el-inspector-status" style="color:#5DCAA5;font:11px/1.4 sans-serif;align-self:center"></span>' +
                '</div>' +
                // Migas de pan clicables (regla #155): "Cadena de contenedores"
                // ya estaba en el texto plano, ilegible como lista de saltos.
                // pointer-events:auto explicito por la misma razon que btnrow:
                // el <pre> de abajo es plano (pre-wrap) y el tip contenedor
                // puede estar en pointer-events:none si todavia no esta fijado.
                '<div id="el-inspector-migas" style="display:none;flex-wrap:wrap;align-items:center;gap:1px;padding:0 0 6px;margin-bottom:6px;border-bottom:1px solid #2a2a35;pointer-events:auto"></div>' +
                '<pre id="el-inspector-text" style="margin:0;font:12px/1.55 \\'Courier New\\',monospace;color:var(--border);white-space:pre-wrap"></pre>';
            doc.body.appendChild(tip);

            var boton = doc.getElementById('el-inspector-copiar');
            var status = doc.getElementById('el-inspector-status');
            var pinBtn = doc.getElementById('el-inspector-pin');
            boton.addEventListener('click', function(ev) {
                ev.preventDefault(); ev.stopPropagation();
                win.__inspectorEjecutarCopia && win.__inspectorEjecutarCopia();
            });

            pinBtn.addEventListener('click', function(ev) {
                ev.preventDefault(); ev.stopPropagation();
                win.__inspectorTogglePin && win.__inspectorTogglePin();
            });
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
            badge.innerHTML = 'Inspector ON' +
                '&nbsp;<button id="el-inspector-silenciar-btn" style="background:rgba(255,255,255,.18);color:#fff;border:0;padding:3px 9px;border-radius:12px;cursor:pointer;font:600 11px/1.4 sans-serif">\\uD83D\\uDC41 Ocultar tooltip</button>' +
                '&nbsp;<span style="opacity:.6;font-weight:400">C copiar &middot; clic-derecho fija y copia &middot; T oculta tooltip &middot; Alt+I salir</span>';
            doc.body.appendChild(badge);

            var silenciarBtn = doc.getElementById('el-inspector-silenciar-btn');
            silenciarBtn.addEventListener('click', function(ev) {
                ev.preventDefault(); ev.stopPropagation();
                win.__inspectorAlternarSilenciado && win.__inspectorAlternarSilenciado();
            });
        }

        function actualizarBadge() {
            badge.style.display = inspectorActivo() ? 'flex' : 'none';
            var silenciarBtn = doc.getElementById('el-inspector-silenciar-btn');
            if (silenciarBtn) {
                silenciarBtn.textContent = win.__inspectorTooltipSilenciado
                    ? '👁 Mostrar tooltip' : '👁 Ocultar tooltip';
            }
        }
        actualizarBadge();

        // Compartido por el boton del badge y el atajo Alt+T. Se reasigna en
        // win en cada rerun (mismo motivo que __inspectorEjecutarCopia mas
        // abajo: el realm del iframe que lo definio puede haber muerto).
        win.__inspectorAlternarSilenciado = function() {
            win.__inspectorTooltipSilenciado = !win.__inspectorTooltipSilenciado;
            actualizarBadge();
            // apagar de inmediato si se acaba de silenciar y no hay nada fijado
            if (win.__inspectorTooltipSilenciado && !win.__inspectorPinned) {
                var tipS = doc.getElementById('el-inspector-tip');
                if (tipS) tipS.style.opacity = '0';
                resaltarEl(null, null);
            }
        };

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

            var railBadge = el.closest('.rail-cat-badge');
            if (railBadge) {
                return '[titulo] titulo de seccion del rail\\n  texto: ' + railBadge.innerText.trim();
            }
            var railSep = el.closest('.rail-sep');
            if (railSep) {
                return '[sep] separador del rail (decorativo)';
            }

            var caption = el.closest('[data-testid="stCaptionContainer"]');
            if (caption) {
                return '[i] caption\\n  ' + caption.textContent.trim().slice(0, 80);
            }

            // FALLBACK: si esta dentro de un st-key-* pero no reconocimos el tipo,
            // igual mostramos un tooltip minimo con el tag/texto. Asi cualquier
            // elemento dentro de la app da AL MENOS los datos de contexto (key,
            // codigo, estilos, cadena) que son lo que mas sirve para pedirle a la IA.
            var cont = el.closest('[class*="st-key-"]');
            if (cont) {
                var tag = (el.tagName || 'DIV').toLowerCase();
                var txt = (el.innerText || '').trim().replace(/\\s+/g, ' ');
                if (txt.length > 60) txt = txt.slice(0, 57) + '...';
                var lines = ['[' + tag + '] elemento generico'];
                if (txt) lines.push('  texto: ' + txt);
                return lines.join('\\n');
            }

            return null;
        }

        function franjaEnCoords(x, y) {
            // Fallback para las franjas fijas superior/inferior. Ambas se pintan
            // con pseudo-elementos (::before / ::after) y/o llevan pointer-events:
            // none, asi que e.target nunca cae en su nodo real. Al hoverear su
            // area visual, mapeamos manualmente al st-key correspondiente para
            // que el usuario pueda copiar contexto y decirle a la IA "esta zona".
            var vh = win.innerHeight;
            var vw = win.innerWidth;
            // Rail izquierdo (~90px). Fuera del rail = a partir de x=90.
            var xUtil = x >= 90;
            if (!xUtil) return null;
            // Franja superior: 0..var(--cab-altura). Leemos la variable en runtime
            // para no hardcodear el 50px por si cambia en base.
            var altoCab = 50;
            try {
                var v = win.getComputedStyle(doc.documentElement)
                          .getPropertyValue('--cab-altura').trim();
                if (v.endsWith('px')) altoCab = parseFloat(v) || 50;
            } catch(_){}
            if (y >= 0 && y <= altoCab) {
                var f = doc.querySelector('.st-key-fila_ajuste_top');
                if (f) return { el: f, etiqueta:
                    '[franja] Franja superior fija\\n' +
                    '  pintada por: .st-key-fila_ajuste_top::before (position:fixed)\\n' +
                    '  nota: pseudo-elemento — el mouse no lo toca; contexto por ubicacion' };
            }
            // Franja inferior: ultimos ~42px (coincide con altura .stApp::after).
            if (y >= vh - 42 && y <= vh && x <= vw) {
                var f2 = doc.querySelector('.st-key-footer_actualizacion');
                if (f2) return { el: f2, etiqueta:
                    '[franja] Franja inferior fija (hora de actualizacion)\\n' +
                    '  pintada por: .stApp::after (position:fixed) + .st-key-footer_actualizacion\\n' +
                    '  nota: pointer-events:none — el mouse la atraviesa; contexto por ubicacion' };
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

        // Los listeners se registran en window.parent (el documento de la app)
        // pero las funciones que los implementan viven en el CONTEXTO del iframe
        // que components.html() crea. En cada rerun de Streamlit, ese iframe se
        // destruye y se crea uno nuevo — los listeners viejos quedan colgados
        // apuntando a funciones muertas del iframe descartado, y el tooltip
        // deja de responder. Por eso guardamos las referencias en win y en cada
        // rerun removemos los viejos e instalamos los del iframe actual.
        if (win.__inspectorMouseMoveHandler) {
            doc.removeEventListener('mousemove', win.__inspectorMouseMoveHandler, true);
        }
        if (win.__inspectorMouseLeaveHandler) {
            doc.removeEventListener('mouseleave', win.__inspectorMouseLeaveHandler);
        }
        if (win.__inspectorKeydownHandler) {
            doc.removeEventListener('keydown', win.__inspectorKeydownHandler);
        }
        if (win.__inspectorPopstateHandler) {
            win.removeEventListener('popstate', win.__inspectorPopstateHandler);
        }
        if (win.__inspectorContextMenuHandler) {
            doc.removeEventListener('contextmenu', win.__inspectorContextMenuHandler);
        }

        // Fijado: clic derecho (o el boton "Fijar") congela el tooltip actual
        // para poder moverse hasta el boton "Copiar" sin que desaparezca —
        // mousemove deja de tocar contenido/posicion mientras esta fijado.
        // Clic derecho ADEMAS copia en el mismo gesto (ver __inspectorEjecutarCopia
        // mas abajo) — asi "clic derecho" por si solo ya resuelve el caso de uso
        // mas comun. El boton "Fijar" se deja aparte para cuando se quiere mirar
        // sin copiar todavia.
        if (win.__inspectorPinned === undefined) win.__inspectorPinned = false;
        // Silenciar tooltip: Alt+T. Solo afecta la VISIBILIDAD del tooltip en
        // hover pasivo — __inspectorUltimo se sigue actualizando igual (lo
        // necesita el pin y el modo diseño), y un elemento FIJADO se sigue
        // mostrando siempre, silenciado o no (ver __inspectorContextMenuHandler).
        if (win.__inspectorTooltipSilenciado === undefined) win.__inspectorTooltipSilenciado = false;

        win.__inspectorTogglePin = function(forzarOff) {
            var tipEl = doc.getElementById('el-inspector-tip');
            var pinBtnEl = doc.getElementById('el-inspector-pin');
            var pinear = forzarOff ? false : !win.__inspectorPinned;
            if (pinear && !win.__inspectorUltimo) return; // nada que fijar
            win.__inspectorPinned = pinear;
            if (tipEl) tipEl.style.pointerEvents = pinear ? 'auto' : 'none';
            if (pinBtnEl) {
                pinBtnEl.textContent = pinear ? '\\uD83D\\uDCCC Fijado (clic para soltar)' : '\\uD83D\\uDCCC Fijar';
                pinBtnEl.style.background = pinear ? '#3C3489' : '#2A2A35';
            }
            if (!pinear && tipEl) tipEl.style.opacity = '0'; // el proximo mousemove lo re-muestra si corresponde
        };

        // Logica de copiado compartida por el boton "Copiar para IA", la tecla
        // C y el clic derecho. Se reasigna en win en cada rerun por el mismo
        // motivo que TogglePin/ContextMenuHandler: el realm del iframe de
        // components.html que la definio pudo haber sido destruido por un
        // rerun anterior (ver comentario grande mas abajo).
        win.__inspectorEjecutarCopia = function() {
            var status = doc.getElementById('el-inspector-status');
            if (!win.__inspectorUltimo) {
                if (status) {
                    status.textContent = 'Primero pasa el mouse por un elemento';
                    status.style.color = '#F0997B';
                    setTimeout(function(){ status.textContent=''; }, 1800);
                }
                return;
            }
            var u = win.__inspectorUltimo;
            var conflictos = [];
            var matcheantes = {};
            var matcheantesPadreKey = null;
            var elBase = u.elementoOriginal || u.elemento;
            try { conflictos  = analizarConflictos(elBase); } catch(_){}
            try { matcheantes = reglasQueMatchean(elBase); } catch(_){}
            // Reglas que le aplican al ancestro keyed (el reportado como
            // "Padre: st-key-X"). Sin esto se ve el margin negativo del
            // padre en los estilos computados pero no queda claro que
            // regla de estilos/ lo produce.
            try {
                var _mio = contenedorConKey(elBase);
                var _up  = _mio ? contenedorConKey(_mio.el.parentElement) : null;
                if (_up) matcheantesPadreKey = reglasQueMatchean(_up.el);
            } catch(_){}
            var extras2Copia = {};
            if (u.extras2) for (var _k in u.extras2) extras2Copia[_k] = u.extras2[_k];
            extras2Copia.matcheantesPadreKey = matcheantesPadreKey;
            extras2Copia.padreKeyNombre = (u.ctx && u.ctx.padre) || '';
            // Wildcards compartidos: recorre TODAS las hojas de estilo, asi
            // que va diferido a la C igual que conflictos/matcheantes (no en
            // cada mousemove). Se calcula sobre el ancestro keyed, que es el
            // que suele traer el margen que uno tiene ganas de tocar.
            try {
                var _mio2 = contenedorConKey(elBase);
                var _up2  = _mio2 ? contenedorConKey(_mio2.el.parentElement) : null;
                extras2Copia.compartidos = selectoresCompartidos(_up2 ? _up2.el : elBase);
            } catch(_){}
            // Variables CSS: junto el cssText AUTORADO de las reglas que
            // matchean (preserva los var() sin resolver) y las resuelvo
            // contra el elemento. Aca (al copiar) ya tengo matcheantes.
            try {
                var _textoReglas = '';
                for (var _a in matcheantes) {
                    for (var _q = 0; _q < matcheantes[_a].length; _q++)
                        _textoReglas += ' ' + (matcheantes[_a][_q].props || '');
                }
                if (matcheantesPadreKey) {
                    for (var _a2 in matcheantesPadreKey) {
                        for (var _q2 = 0; _q2 < matcheantesPadreKey[_a2].length; _q2++)
                            _textoReglas += ' ' + (matcheantesPadreKey[_a2][_q2].props || '');
                    }
                }
                extras2Copia.varsCSS = varsEnTexto(elBase, _textoReglas);
            } catch(_) {}
            var texto = bloqueParaIA(u.etiqueta, u.key, u.ctx, u.medidas, u.pagina, conflictos, matcheantes, extras2Copia);
            copiarTexto(texto,
                function(){
                    if (status) { status.textContent = 'Copiado (' + texto.length + ' chars)'; status.style.color = '#5DCAA5'; setTimeout(function(){ status.textContent=''; }, 1800); }
                },
                function(){
                    // Clipboard API y execCommand fallaron (comun en el iframe
                    // anidado de Streamlit Cloud si el documento perdio el
                    // foco). Ultimo recurso: dejar el texto SELECCIONADO para
                    // que un Ctrl+C fisico del usuario funcione — eso es un
                    // gesto real, no sujeto a las mismas restricciones.
                    if (status) { status.textContent = 'Automatico bloqueado: texto seleccionado, Ctrl+C'; status.style.color = '#F0997B'; }
                    win.console && win.console.log('[INSPECTOR COPY]\\n' + texto);
                    try {
                        var preEl = doc.getElementById('el-inspector-text');
                        if (preEl) {
                            var range = doc.createRange();
                            range.selectNodeContents(preEl);
                            var sel = win.getSelection();
                            sel.removeAllRanges();
                            sel.addRange(range);
                        }
                    } catch(_){}
                }
            );
        };

        win.__inspectorContextMenuHandler = function(e) {
            if (!inspectorActivo()) return;
            var tipEl = doc.getElementById('el-inspector-tip');
            if (!tipEl) return;
            if (win.__inspectorPinned) {
                e.preventDefault();
                win.__inspectorTogglePin(true);
                // recalcular de inmediato en la posicion actual del cursor,
                // si no queda invisible hasta el proximo mousemove real
                if (win.__inspectorMouseMoveHandler) win.__inspectorMouseMoveHandler(e);
                return;
            }
            if (!win.__inspectorUltimo) return; // no hay nada bajo el cursor para fijar
            e.preventDefault();
            win.__inspectorTogglePin();
            // Silenciado (Alt+T / boton del badge): fijar NO debe revelar el
            // tooltip — el usuario lo apago justamente para que clic-derecho-
            // para-seleccionar no le tape la pantalla. __inspectorUltimo ya
            // esta actualizado (lo necesitan el pin y el modo diseño), asi
            // que fijar sigue funcionando igual; solo cambia la visibilidad.
            if (tipEl && !win.__inspectorTooltipSilenciado) {
                var txp = e.clientX + 16, typ = e.clientY - 10;
                var twp = tipEl.offsetWidth || 260, thp = tipEl.offsetHeight || 80;
                if (txp + twp > win.innerWidth - 8) txp = e.clientX - twp - 16;
                if (typ + thp > win.innerHeight - 8) typ = e.clientY - thp - 10;
                if (typ < 6) typ = 6;
                tipEl.style.opacity = '1';
                tipEl.style.left = txp + 'px';
                tipEl.style.top = typ + 'px';
            }
            win.__inspectorEjecutarCopia && win.__inspectorEjecutarCopia(); // un solo gesto: fija Y copia
        };

        win.__inspectorMouseMoveHandler = function(e) {
              try {
                var tip = doc.getElementById('el-inspector-tip');
                if (!tip) return;
                if (!inspectorActivo()) {
                    tip.style.opacity = '0';
                    resaltarEl(null, null);
                    return;
                }
                if (win.__inspectorPinned) return; // fijado: no tocar contenido/posicion
                // congelar contenido mientras el cursor esta sobre el tooltip
                // (asi se puede leer y scrollear sin que salte al widget de al lado)
                if (tip.contains(e.target) || e.target === tip) return;

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
                if (!etiqueta) {
                    // Franjas fijas (superior/inferior) — nunca son e.target
                    // porque son pseudo-elementos y/o pointer-events:none.
                    var fj = null;
                    try { fj = franjaEnCoords(e.clientX, e.clientY); } catch(err) { fj = null; }
                    if (fj) { el = fj.el; etiqueta = fj.etiqueta; }
                }
                if (etiqueta) resaltarEl(el, etiqueta);
                else resaltarEl(null, null);
            }

            if (etiqueta) {
                // enriquecemos con codigo/estilos/padre/hermanos derivados del key del ancestro
                var ctxCont = contenedorConKey(el);
                var ctxKey  = ctxCont ? ctxCont.key : '';
                var ctxCod  = buscarCodigo(ctxKey);
                var ctxEst  = buscarEstilos(ctxKey);
                var ctxRel  = padreYHermanos(el);
                var medidas = medirElemento(ctxCont ? ctxCont.el : el);
                var pagina  = contextoPagina();
                var testids = cadenaTestids(el);
                var clases  = clasesElemento(el);
                var keysCad = cadenaKeys(el);
                // Baratas (recorridos de DOM, no de hojas de estilo): van en
                // el hover. `compartidos` no — ese recorre styleSheets y se
                // computa al pulsar C. Ver regla #90.
                var ancla   = anclaPropia(el);
                var pesos   = pesoAncestros(el);
                var ctxFunc = buscarFuncion(ctxKey);
                var ctxRefs = buscarRefs(ctxKey);
                var ctxSS   = buscarSS(ctxKey);
                var ctxConstruido = buscarConstruido(ctxKey);
                // Origen del texto: si el widget tiene texto visible (caption,
                // button, p) y matchea un literal st.XXX("...") del codebase.
                var ctxOrigenTxt = '';
                try {
                    var _txt = (el.innerText || '').trim();
                    if (_txt) ctxOrigenTxt = buscarPorTexto(_txt);
                } catch(_) {}
                // conflictos y reglasQueMatchean: calculo diferido (solo al copiar) - son O(reglas*props),
                // no queremos correrlos en cada mousemove.
                var ctxSnippet = buscarSnippet(ctxKey);
                var lp = layoutPadre(el);
                var bp = boxPadre(el);
                var bpk = boxPadreKey(el);
                // Pseudo-elementos del contenedor keyed (ahi viven los ::before/
                // ::after del proyecto). Baratos: dos getComputedStyle. Las vars
                // resueltas se agregan solo al copiar (necesitan las reglas
                // matcheantes, que son O(reglas*props) y van diferidas a la C).
                var elPseudo = ctxCont ? ctxCont.el : el;
                var pBefore = pseudoInfo(elPseudo, '::before');
                var pAfter  = pseudoInfo(elPseudo, '::after');
                // Tooltip = mismo formato que "copiar para IA", pero sin
                // conflictos/reglas-que-matchean (esos se computan al pulsar C).
                var ctxHover = { codigo: ctxCod, estilos: ctxEst,
                                 padre: ctxRel.padre, hermanos: ctxRel.hermanos,
                                 snippet: ctxSnippet,
                                 funcion: ctxFunc, refs: ctxRefs, ss: ctxSS,
                                 origenTexto: ctxOrigenTxt,
                                 construido: ctxConstruido };
                var extras2Hover = { testids: testids, clases: clases, keysCad: keysCad,
                                     layoutPadre: lp, boxPadre: bp, boxPadreKey: bpk,
                                     ancla: ancla, pesos: pesos,
                                     pseudoBefore: pBefore, pseudoAfter: pAfter };
                var etiquetaFinal = bloqueParaIA(etiqueta, ctxKey, ctxHover, medidas,
                                                 pagina, null, null, extras2Hover)
                                    + '\\n[C] copiar para IA (incluye conflictos + reglas matcheantes)';
                win.__inspectorUltimo = {
                    etiqueta: etiqueta, key: ctxKey,
                    ctx: { codigo: ctxCod, estilos: ctxEst,
                           padre: ctxRel.padre, hermanos: ctxRel.hermanos,
                           snippet: ctxSnippet,
                           funcion: ctxFunc, refs: ctxRefs, ss: ctxSS },
                    medidas: medidas, pagina: pagina,
                    extras2: { testids: testids, clases: clases, keysCad: keysCad,
                               layoutPadre: lp, boxPadre: bp, boxPadreKey: bpk,
                               ancla: ancla, pesos: pesos,
                               pseudoBefore: pBefore, pseudoAfter: pAfter },
                    elemento: (ctxCont ? ctxCont.el : el),
                    elementoOriginal: el
                };
                var pre = doc.getElementById('el-inspector-text');
                if (pre) pre.textContent = etiquetaFinal;
                else tip.textContent = etiquetaFinal;
                pintarMigas(keysCad);
                // Silenciado (Alt+T): el hover pasivo no muestra el tooltip
                // (__inspectorUltimo ya se actualizo arriba igual, sin
                // depender de esto). Este bloque nunca corre estando fijado
                // — el handler ya retorna antes, mas arriba — así que fijar
                // siempre revela el tooltip via __inspectorContextMenuHandler,
                // no acá.
                if (!win.__inspectorTooltipSilenciado) {
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
            } else {
                tip.style.opacity = '0';
            }
              } catch(err) {
                if (win.__logErr) win.__logErr('Inspector mousemove: ' + err.message);
              }
            };

            win.__inspectorMouseLeaveHandler = function() {
                if (win.__inspectorPinned) return; // fijado: se queda visible aunque el cursor salga
                var tip = doc.getElementById('el-inspector-tip');
                if (tip) tip.style.opacity = '0';
                resaltarEl(null, null);
            };

            win.__inspectorKeydownHandler = function(e) {
                if ((e.key === 'c' || e.key === 'C') && !e.altKey && !e.ctrlKey && !e.metaKey
                    && inspectorActivo() && win.__inspectorUltimo) {
                    var t = e.target;
                    var tag = t && t.tagName ? t.tagName.toLowerCase() : '';
                    if (tag === 'input' || tag === 'textarea' || (t && t.isContentEditable)) return;
                    e.preventDefault();
                    var btn = doc.getElementById('el-inspector-copiar');
                    if (btn) btn.click();
                    return;
                }
                if (e.key === 'Escape' && win.__inspectorPinned) {
                    win.__inspectorTogglePin(true);
                    return;
                }
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
                        if (win.__inspectorPinned) win.__inspectorTogglePin(true);
                        var tip = doc.getElementById('el-inspector-tip');
                        if (tip) tip.style.opacity = '0';
                        resaltarEl(null, null);
                    }
                }
                if (e.altKey && (e.key === 't' || e.key === 'T') && inspectorActivo()) {
                    win.__inspectorAlternarSilenciado && win.__inspectorAlternarSilenciado();
                }
            };

            win.__inspectorPopstateHandler = actualizarBadge;

            doc.addEventListener('mousemove', win.__inspectorMouseMoveHandler, true);
            doc.addEventListener('mouseleave', win.__inspectorMouseLeaveHandler);
            doc.addEventListener('keydown', win.__inspectorKeydownHandler);
            doc.addEventListener('contextmenu', win.__inspectorContextMenuHandler);
            win.addEventListener('popstate', win.__inspectorPopstateHandler);

            // pushState monkey-patch: solo la PRIMERA vez, para no encadenar
            // wrappers infinitos rerun tras rerun. El wrapper original queda
            // valido porque llama a actualizarBadge por nombre — la variable
            // se resuelve contra el scope actual en cada llamada.
            if (!win.__inspectorPushStatePatched) {
                win.__inspectorPushStatePatched = true;
                var _push = win.history.pushState.bind(win.history);
                win.history.pushState = function() {
                    _push.apply(win.history, arguments);
                    if (win.__inspectorPopstateHandler) win.__inspectorPopstateHandler();
                };
            }

    })();
    </script>
    """
