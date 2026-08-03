"""inyecciones.inspector - inspector de elementos (herramienta de desarrollo).

Permite senalar un elemento en la pagina y ver sus selectores y estilos. Es
la inyeccion mas grande del paquete y no participa del render normal.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components

_RAIZ = Path(__file__).resolve().parent.parent
_KEY_PY = re.compile(r"""key\s*=\s*['"]([A-Za-z0-9_]+)['"]""")
_KEY_CSS = re.compile(r"st-key-([A-Za-z0-9_]+)")
# def / async def top-level (indent 0). Captura el nombre.
_DEF_TOP = re.compile(r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _funcion_contenedora(lineas: list[str], linea_1based: int) -> tuple[str, int, int, bool]:
    """Para una linea dada (1-based), devuelve (nombre_func, ini, fin, es_fragment).
    `es_fragment`: True si la función tiene @st.fragment (o @fragment) arriba.
    Si la linea no cae dentro de ningun `def` de nivel 0, devuelve ('', 0, 0, False).
    """
    idx = linea_1based - 1
    ini_def = -1
    nombre = ""
    for j in range(idx, -1, -1):
        m = _DEF_TOP.match(lineas[j])
        if m:
            ini_def = j
            nombre = m.group(1)
            break
    if ini_def < 0:
        return ("", 0, 0, False)
    # decoradores inmediatamente arriba del def
    es_fragment = False
    j = ini_def - 1
    while j >= 0:
        ln = lineas[j].strip()
        if not ln or ln.startswith("#"):
            j -= 1
            continue
        if ln.startswith("@"):
            if "fragment" in ln:
                es_fragment = True
            j -= 1
            continue
        break
    fin = len(lineas)
    for j in range(ini_def + 1, len(lineas)):
        ln = lineas[j]
        if not ln.strip():
            continue
        if ln[0] not in (" ", "\t", ")", "]", "#"):
            fin = j
            break
    while fin > ini_def + 1 and not lineas[fin - 1].strip():
        fin -= 1
    return (nombre, ini_def + 1, fin, es_fragment)


@lru_cache(maxsize=1)
def _mapas_desarrollador() -> tuple[str, str, str, str, str]:
    """Devuelve (mapa_codigo, mapa_estilos, mapa_snippets, mapa_funcion, mapa_refs).

    mapa_codigo  : {key -> "archivo:linea"}  (primer match gana)
    mapa_estilos : {key_o_prefijo -> ["archivo_estilo.py", ...]}
    mapa_snippets: {key -> "snippet 5 lineas"}
    mapa_funcion : {key -> "nombre_func (archivo:ini-fin)"}
    mapa_refs    : {key -> ["archivo:linea", ...] otras referencias al nombre_func}
    """
    mapa_codigo: dict[str, str] = {}
    mapa_snippets: dict[str, str] = {}
    mapa_funcion: dict[str, str] = {}
    # (nombre_func, archivo_def) por key -> se usa para calcular refs despues
    key_a_func: dict[str, tuple[str, str]] = {}

    fuentes_py = sorted(p for p in _RAIZ.glob("*.py") if not p.name.startswith("_"))
    fuentes_py += sorted((_RAIZ / "graficos").glob("*.py"))
    fuentes_py += sorted((_RAIZ / "graficos" / "compras").glob("*.py")) if (_RAIZ / "graficos" / "compras").exists() else []
    fuentes_py += sorted((_RAIZ / "tablas").glob("*.py")) if (_RAIZ / "tablas").exists() else []

    # cache: {archivo -> [lineas]} para no releer al buscar refs
    contenido_por_archivo: dict[str, list[str]] = {}

    for archivo in fuentes_py:
        try:
            lineas = archivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel = archivo.relative_to(_RAIZ).as_posix()
        contenido_por_archivo[rel] = lineas
        for i, linea in enumerate(lineas, 1):
            for k in _KEY_PY.findall(linea):
                if k not in mapa_codigo:
                    mapa_codigo[k] = f"{rel}:{i}"
                    start = max(0, i - 3)
                    end = min(len(lineas), i + 2)
                    snippet_lines = []
                    for j in range(start, end):
                        prefix = ">>>" if j == i - 1 else "   "
                        snippet_lines.append(f"{prefix} {j+1:>4}| {lineas[j]}")
                    mapa_snippets[k] = "\n".join(snippet_lines)
                    # funcion contenedora
                    nombre, ini, fin, es_frag = _funcion_contenedora(lineas, i)
                    if nombre:
                        tag = " [@st.fragment]" if es_frag else ""
                        mapa_funcion[k] = f"{nombre} ({rel}:{ini}-{fin}){tag}"
                        key_a_func[k] = (nombre, rel)

    # Referencias: por cada key con func, buscar el nombre en todos los .py
    # excepto en la propia linea de definicion. Evita ruido acotando a `\bNAME\b`.
    mapa_refs: dict[str, list[str]] = {}
    # cachear regex por nombre reutilizable entre keys que comparten funcion
    refs_por_nombre: dict[tuple[str, str], list[str]] = {}
    for k, (nombre, archivo_def) in key_a_func.items():
        clave = (nombre, archivo_def)
        if clave in refs_por_nombre:
            mapa_refs[k] = refs_por_nombre[clave]
            continue
        patron = re.compile(rf"\b{re.escape(nombre)}\b")
        refs: list[str] = []
        for rel, lineas_a in contenido_por_archivo.items():
            for i, linea in enumerate(lineas_a, 1):
                if not patron.search(linea):
                    continue
                # saltar la propia def
                m = _DEF_TOP.match(linea)
                if m and m.group(1) == nombre and rel == archivo_def:
                    continue
                refs.append(f"{rel}:{i}")
                if len(refs) >= 8:
                    break
            if len(refs) >= 8:
                break
        refs_por_nombre[clave] = refs
        mapa_refs[k] = refs

    mapa_estilos: dict[str, list[str]] = {}
    for archivo in sorted((_RAIZ / "estilos").glob("*.py")):
        try:
            texto = archivo.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = archivo.relative_to(_RAIZ).as_posix()
        for k in set(_KEY_CSS.findall(texto)):
            k_norm = k.rstrip("_")
            if not k_norm:
                continue
            mapa_estilos.setdefault(k_norm, [])
            if rel not in mapa_estilos[k_norm]:
                mapa_estilos[k_norm].append(rel)

    return (
        json.dumps(mapa_codigo),
        json.dumps(mapa_estilos),
        json.dumps(mapa_snippets),
        json.dumps(mapa_funcion),
        json.dumps(mapa_refs),
    )


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
    mapa_codigo, mapa_estilos, mapa_snippets, mapa_funcion, mapa_refs = _mapas_desarrollador()
    # session_state: snapshot no cacheado (cambia cada rerun). Se serializa a
    # str truncado — solo para inspección; nunca para persistir.
    import streamlit as st
    _ss_snapshot: dict[str, str] = {}
    try:
        for _k, _v in st.session_state.items():
            if not isinstance(_k, str) or _k.startswith("_"):
                continue
            try:
                _s = repr(_v)
            except Exception:
                _s = f"<{type(_v).__name__}>"
            if len(_s) > 80:
                _s = _s[:77] + "..."
            _ss_snapshot[_k] = _s
    except Exception:
        pass
    mapa_ss = json.dumps(_ss_snapshot)
    components.html("""
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;

        win.__inspectorMapaCodigo  = __MAPA_CODIGO__;
        win.__inspectorMapaEstilos = __MAPA_ESTILOS__;
        win.__inspectorMapaSnippets = __MAPA_SNIPPETS__;
        win.__inspectorMapaFuncion = __MAPA_FUNCION__;
        win.__inspectorMapaRefs    = __MAPA_REFS__;
        win.__inspectorSS          = __MAPA_SS__;

        function buscarCodigo(key) {
            if (!key) return '';
            return win.__inspectorMapaCodigo[key] || '';
        }
        function buscarSnippet(key) {
            if (!key) return '';
            return win.__inspectorMapaSnippets[key] || '';
        }
        function buscarFuncion(key) {
            if (!key) return '';
            return win.__inspectorMapaFuncion[key] || '';
        }
        function buscarRefs(key) {
            if (!key) return [];
            return win.__inspectorMapaRefs[key] || [];
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
            return { padre: arriba.key, hermanos: hermanos.slice(0, 6) };
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
            return {
                tamano: Math.round(r.width) + ' x ' + Math.round(r.height) + ' px',
                coords: coords + (visible ? '' : ' (FUERA DEL VIEWPORT)'),
                estilos: {
                    'font-size'   : pick('font-size'),
                    'color'       : pick('color'),
                    'background'  : pick('background-color'),
                    'padding'     : pick('padding'),
                    'margin'      : pick('margin'),
                    'border-radius': pick('border-radius')
                }
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
                var reporte = u.searchParams.get('reporte') || u.searchParams.get('r') || '(no en URL)';
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
        function boxPadre(el) {
            var cont = contenedorConKey(el);
            if (!cont) return '';
            var padre = cont.el.parentElement;
            if (!padre) return '';
            var cs = win.getComputedStyle(padre);
            var m = cs.margin || (cs.marginTop + ' ' + cs.marginRight + ' ' + cs.marginBottom + ' ' + cs.marginLeft);
            var p = cs.padding || (cs.paddingTop + ' ' + cs.paddingRight + ' ' + cs.paddingBottom + ' ' + cs.paddingLeft);
            var partes = [];
            if (m && m !== '0px' && m !== '0px 0px 0px 0px') partes.push('margin=' + m);
            if (p && p !== '0px' && p !== '0px 0px 0px 0px') partes.push('padding=' + p);
            return partes.join(' | ');
        }
        function bloqueParaIA(etiqueta, key, ctx, medidas, pagina, conflictos, matcheantes, extras2) {
            var lines = ['--- copiar para IA ---'];
            lines.push('Widget key: ' + (key || '(sin key)'));
            if (ctx.codigo)   lines.push('Declarado en: ' + ctx.codigo);
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
                if (extras2.keysCad && extras2.keysCad.length)
                    lines.push('Cadena de contenedores st-key (elemento -> raiz): ' + extras2.keysCad.join(' > '));
                if (extras2.testids && extras2.testids.length)
                    lines.push('Cadena de data-testid (elemento -> raiz): ' + extras2.testids.join(' > '));
                if (extras2.clases && extras2.clases.length)
                    lines.push('Clases del elemento hovereado (NO de contenedores): ' + extras2.clases.join(' '));
                if (extras2.layoutPadre)
                    lines.push('Layout del padre: ' + extras2.layoutPadre);
                if (extras2.boxPadre)
                    lines.push('Box del padre: ' + extras2.boxPadre);
            }
            if (matcheantes) {
                var archs = Object.keys(matcheantes);
                if (archs.length) {
                    lines.push('Reglas de estilos/ que matchean este elemento:');
                    for (var a = 0; a < archs.length; a++) {
                        var reglas = matcheantes[archs[a]];
                        lines.push('  ' + archs[a] + ' (' + reglas.length + ' regla' + (reglas.length > 1 ? 's' : '') + '):');
                        for (var si2 = 0; si2 < reglas.length && si2 < 4; si2++) {
                            lines.push('     ' + reglas[si2].sel);
                            if (reglas[si2].props) lines.push('       { ' + reglas[si2].props + ' }');
                        }
                        if (reglas.length > 4) lines.push('     ...(' + (reglas.length - 4) + ' mas)');
                    }
                }
            }
            var flat = formatearConflictos(conflictos);
            for (var i = 0; i < flat.length; i++) lines.push(flat[i]);
            if (ctx.snippet) lines.push('Codigo Python (contexto):\\n' + ctx.snippet);
            if (etiqueta) lines.push('Detalle:\\n' + etiqueta);
            return lines.join('\\n');
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
                // pointer-events:auto para poder scrollear la rueda del mouse
                // adentro; congelamos el contenido cuando el cursor entra en
                // el tooltip (ver mousemove handler)
                'pointer-events:auto',
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
                '<div id="el-inspector-btnrow" style="position:sticky;top:-7px;background:#101014;padding:4px 0 6px;margin:-1px 0 6px;border-bottom:1px solid #3C3489;display:flex;gap:6px;z-index:1">' +
                '  <button id="el-inspector-copiar" style="background:#3C3489;color:#fff;border:0;padding:5px 10px;border-radius:4px;cursor:pointer;font:600 11px/1 sans-serif">Copiar para IA</button>' +
                '  <span id="el-inspector-status" style="color:#5DCAA5;font:11px/1.4 sans-serif;align-self:center"></span>' +
                '</div>' +
                '<pre id="el-inspector-text" style="margin:0;font:12px/1.55 \\'Courier New\\',monospace;color:var(--border);white-space:pre-wrap"></pre>';
            doc.body.appendChild(tip);

            var boton = doc.getElementById('el-inspector-copiar');
            var status = doc.getElementById('el-inspector-status');
            boton.addEventListener('click', function(ev) {
                ev.preventDefault(); ev.stopPropagation();
                if (!win.__inspectorUltimo) {
                    status.textContent = 'Primero pasa el mouse por un elemento';
                    status.style.color = '#F0997B';
                    setTimeout(function(){ status.textContent=''; }, 1800);
                    return;
                }
                var u = win.__inspectorUltimo;
                var conflictos = [];
                var matcheantes = {};
                try { conflictos  = analizarConflictos(u.elementoOriginal || u.elemento); } catch(_){}
                try { matcheantes = reglasQueMatchean(u.elementoOriginal || u.elemento); } catch(_){}
                var texto = bloqueParaIA(u.etiqueta, u.key, u.ctx, u.medidas, u.pagina, conflictos, matcheantes, u.extras2);
                copiarTexto(texto,
                    function(){ status.textContent = 'Copiado (' + texto.length + ' chars)'; status.style.color = '#5DCAA5'; setTimeout(function(){ status.textContent=''; }, 1800); },
                    function(){ status.textContent = 'No pude copiar - abre consola para ver texto'; status.style.color = '#F0997B'; win.console && win.console.log('[INSPECTOR COPY]\\n' + texto); setTimeout(function(){ status.textContent=''; }, 3000); }
                );
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
            badge.innerHTML = 'Inspector ON &nbsp;<span style="opacity:.6;font-weight:400">C copiar &middot; Alt+I salir</span>';
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
                var ctxFunc = buscarFuncion(ctxKey);
                var ctxRefs = buscarRefs(ctxKey);
                var ctxSS   = buscarSS(ctxKey);
                // conflictos y reglasQueMatchean: calculo diferido (solo al copiar) - son O(reglas*props),
                // no queremos correrlos en cada mousemove.
                var ctxSnippet = buscarSnippet(ctxKey);
                var lp = layoutPadre(el);
                var bp = boxPadre(el);
                // Tooltip = mismo formato que "copiar para IA", pero sin
                // conflictos/reglas-que-matchean (esos se computan al pulsar C).
                var ctxHover = { codigo: ctxCod, estilos: ctxEst,
                                 padre: ctxRel.padre, hermanos: ctxRel.hermanos,
                                 snippet: ctxSnippet,
                                 funcion: ctxFunc, refs: ctxRefs, ss: ctxSS };
                var extras2Hover = { testids: testids, clases: clases, keysCad: keysCad,
                                     layoutPadre: lp, boxPadre: bp };
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
                               layoutPadre: lp, boxPadre: bp },
                    elemento: (ctxCont ? ctxCont.el : el),
                    elementoOriginal: el
                };
                var pre = doc.getElementById('el-inspector-text');
                if (pre) pre.textContent = etiquetaFinal;
                else tip.textContent = etiquetaFinal;
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
    """.replace("__MAPA_CODIGO__", mapa_codigo).replace("__MAPA_ESTILOS__", mapa_estilos).replace("__MAPA_SNIPPETS__", mapa_snippets).replace("__MAPA_FUNCION__", mapa_funcion).replace("__MAPA_REFS__", mapa_refs).replace("__MAPA_SS__", mapa_ss),
        height=0, scrolling=False)
