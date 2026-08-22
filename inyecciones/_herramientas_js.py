"""inyecciones._herramientas_js - el JS de la barra unificada de herramientas.

Separado de `herramientas.py` por el mismo motivo que `_inspector_js.py` y
`_diseno_js.py`: un bloque grande de JS embebido dentro del `.py` que lo
inyecta tapa la logica de Python. Aca solo vive el script; la sustitucion de
`__FUENTES__` (el codigo de los auditores de `herramientas/`) la hace
`herramientas.py`.

Ver el docstring de `herramientas.py` para QUE hace la barra, como se activa
y su acoplamiento con inspector.py.
"""

JS = """
<script>
(function () {
    var win = window.parent;
    var doc = win && win.document;
    if (!win || !doc || !doc.body) return;

    // ── Fuentes de los auditores, embebidas por herramientas.py ───────────
    // Son los MISMOS ficheros de herramientas/*.js que se pegan en la
    // consola: una sola fuente, dos formas de correrlos (ver el docstring
    // de herramientas.py).
    var FUENTES = __FUENTES__;

    // Los .js de herramientas/ estan escritos para la CONSOLA: usan
    // `document`/`window` directo. Ejecutarlos aca (dentro del iframe de
    // components.html) los dejaria midiendo el DOM del iframe, que esta
    // vacio. Un <script> creado en el documento del PADRE corre en su
    // realm, asi que definen win.rayosX / win.auditar / win.auditarGraficos
    // sobre la app real. Es la misma razon por la que todo este script
    // trabaja contra `win`/`doc` y no contra su propio window.
    function cargarFuente(nombre, definido) {
        if (win[definido]) return true;          // ya cargada en este realm
        var codigo = FUENTES[nombre];
        if (!codigo) return false;
        try {
            var s = doc.createElement('script');
            s.setAttribute('data-herramienta', nombre);
            s.textContent = codigo;
            doc.body.appendChild(s);
        } catch (err) {
            console.warn('[herramientas] no se pudo cargar ' + nombre, err);
            return false;
        }
        return !!win[definido];
    }

    // ── Estado por URL, igual que inspector.py y diseno.py ────────────────
    // Que cada modo sea un query param (y no una variable en memoria) es a
    // proposito: la URL queda compartible/marcable y sobrevive el rerun de
    // Streamlit sin estado extra. Mismo idiom que el Alt+I del inspector.
    function activo(param) {
        return new URL(win.location.href).searchParams.get(param) === '1';
    }
    function fijar(param, valor) {
        var url = new URL(win.location.href);
        if (valor) url.searchParams.set(param, '1');
        else url.searchParams.delete(param);
        win.history.replaceState({}, '', url.toString());
    }

    function barraVisible() { return activo('debug'); }

    // ── Paleta (la del modo diseno, para que se lean como una familia) ────
    var FONDO = '#101014', TEXTO = '#cfcfd6', BORDE = '#2a2a35';
    var ACENTO = '#6c5ce7', AVISO = '#e1a100';

    // =====================================================================
    // PANEL DE RESULTADOS (los dos auditores)
    // =====================================================================
    var ID_PANEL = 'herr-panel';

    function cerrarPanel() {
        var p = doc.getElementById(ID_PANEL);
        if (p) p.remove();
    }

    function abrirPanel(titulo) {
        cerrarPanel();
        var p = doc.createElement('div');
        p.id = ID_PANEL;
        p.style.cssText = [
            'position:fixed', 'left:72px', 'bottom:88px',
            'width:min(680px, calc(100vw - 100px))',
            'max-height:min(60vh, 520px)', 'overflow:auto',
            'z-index:2147483645',
            'background:' + FONDO, 'color:' + TEXTO,
            'border:1px solid ' + BORDE, 'border-radius:8px',
            'padding:10px 12px 12px',
            'font:12px/1.45 -apple-system,BlinkMacSystemFont,sans-serif',
            'box-shadow:0 6px 24px rgba(0,0,0,.45)',
        ].join(';');

        var cab = doc.createElement('div');
        cab.style.cssText = 'display:flex;align-items:center;justify-content:space-between;'
                          + 'margin:0 0 8px;padding-bottom:6px;border-bottom:1px solid ' + BORDE;
        var h = doc.createElement('b');
        h.textContent = titulo;
        h.style.cssText = 'color:#fff;font-size:12px';
        var x = doc.createElement('button');
        x.textContent = '✕';
        x.style.cssText = 'background:transparent;border:0;color:' + TEXTO
                        + ';cursor:pointer;font-size:14px;line-height:1;padding:2px 4px';
        x.addEventListener('click', cerrarPanel);
        cab.appendChild(h); cab.appendChild(x);
        p.appendChild(cab);
        doc.body.appendChild(p);
        return p;
    }

    function seccion(panel, titulo, color) {
        var d = doc.createElement('div');
        d.textContent = titulo;
        d.style.cssText = 'font-size:10px;letter-spacing:.04em;text-transform:uppercase;'
                        + 'margin:12px 0 4px;color:' + (color || '#6f6f7a');
        panel.appendChild(d);
        return d;
    }

    // Tabla generica desde un array de objetos. Los valores van por
    // textContent (nunca innerHTML): esto lee el DOM de la app, y el
    // contenido real de una celda puede ser cualquier cosa.
    function tabla(panel, filas, columnas) {
        if (!filas || !filas.length) return;
        var cols = columnas || Object.keys(filas[0]);
        var t = doc.createElement('table');
        t.style.cssText = 'width:100%;border-collapse:collapse;font-size:11px';
        var thead = doc.createElement('tr');
        cols.forEach(function (c) {
            var th = doc.createElement('th');
            th.textContent = c;
            th.style.cssText = 'text-align:left;padding:3px 6px 3px 0;color:#8b8b96;'
                             + 'font-weight:600;border-bottom:1px solid ' + BORDE;
            thead.appendChild(th);
        });
        t.appendChild(thead);
        filas.forEach(function (f) {
            var tr = doc.createElement('tr');
            cols.forEach(function (c) {
                var td = doc.createElement('td');
                var v = f[c];
                td.textContent = (v === null || v === undefined) ? '—'
                               : (typeof v === 'object' ? JSON.stringify(v) : String(v));
                td.style.cssText = 'padding:3px 6px 3px 0;border-bottom:1px solid #1c1c24;'
                                 + 'font-variant-numeric:tabular-nums';
                tr.appendChild(td);
            });
            t.appendChild(tr);
        });
        panel.appendChild(t);
    }

    function nota(panel, texto, color) {
        var d = doc.createElement('div');
        d.textContent = texto;
        d.style.cssText = 'font-size:11px;margin:4px 0;color:' + (color || TEXTO);
        panel.appendChild(d);
    }

    // ── Auditor de layout ────────────────────────────────────────────────
    function correrLayout() {
        if (!cargarFuente('auditar_layout', 'auditar')) {
            var pe = abrirPanel('Auditar layout');
            nota(pe, 'No se pudo cargar herramientas/auditar_layout.js', '#e17055');
            return;
        }
        var r;
        try { r = win.auditar(); }
        catch (err) {
            var pf = abrirPanel('Auditar layout');
            nota(pf, 'Fallo al auditar: ' + err.message, '#e17055');
            return;
        }
        var p = abrirPanel('Auditar layout');
        nota(p, r.viewport[0] + '×' + r.viewport[1] + ' px · ancho útil '
              + r.anchoUtil + ' px · ' + r.totalContenedores + ' contenedores con key');

        if (r.desbordeHorizontalPx) {
            seccion(p, 'Desborde horizontal: ' + r.desbordeHorizontalPx + ' px', '#e17055');
            tabla(p, r.culpablesDesborde, ['key', 'tag', 'w', 'right']);
        }
        if (r.alertas && r.alertas.length) {
            seccion(p, r.alertas.length + ' por encima del umbral', AVISO);
            tabla(p, r.alertas, ['key', 'w', 'h', '%W', '%Vh', 'alerta']);
        }
        if (r.outliersDeFamilia && r.outliersDeFamilia.length) {
            seccion(p, 'Outliers dentro de su familia de key', AVISO);
            tabla(p, r.outliersDeFamilia, ['key', 'familia', 'h', 'medianaFam']);
        }
        if (r.holguras && r.holguras.length) {
            seccion(p, 'Paneles que podrían crecer (alto chico con sitio libre)', AVISO);
            tabla(p, r.holguras, ['key', 'alto', 'recortadoPx', 'podriaCrecerPx', 'marco']);
        }
        seccion(p, 'Top por altura');
        tabla(p, r.topAltos, ['key', 'w', 'h', '%W', '%Vh']);
        if (r.flotantes && r.flotantes.length) {
            seccion(p, r.flotantes.length + ' flotantes (fixed/absolute)');
            tabla(p, r.flotantes, ['key', 'pos', 'w', 'h', 'top', 'left']);
        }
        if (!r.desbordeHorizontalPx && !(r.alertas || []).length
            && !(r.outliersDeFamilia || []).length && !(r.holguras || []).length) {
            nota(p, '✅ Sin alertas.', '#00b894');
        }
    }

    // ── Auditor de gráficos ──────────────────────────────────────────────
    function correrGraficos() {
        if (!cargarFuente('auditar_graficos', 'auditarGraficos')) {
            var pe = abrirPanel('Auditar gráficos');
            nota(pe, 'No se pudo cargar herramientas/auditar_graficos.js', '#e17055');
            return;
        }
        var r;
        try { r = win.auditarGraficos(); }
        catch (err) {
            var pf = abrirPanel('Auditar gráficos');
            nota(pf, 'Fallo al auditar: ' + err.message, '#e17055');
            return;
        }
        var p = abrirPanel('Auditar gráficos');

        // auditarGraficos devuelve {graficos:0} si no hay ninguno, y un
        // ARRAY si los hay. Distinguir por Array.isArray y no por .length:
        // {graficos:0} no tiene length y caeria en el camino equivocado.
        if (!Array.isArray(r)) {
            nota(p, 'No hay ningún gráfico de Plotly en esta pantalla.');
            return;
        }
        var malos = r.filter(function (g) { return !g.ok; });
        nota(p, r.length + ' gráfico(s) · ' + malos.length + ' con problemas',
             malos.length ? '#e17055' : '#00b894');

        // El aviso de la ventana redimensionada no es cosmetico: Plotly no
        // re-maquetea solo y el chequeo reporta recortes falsos (25 de una,
        // ver la cabecera de auditar_graficos.js).
        nota(p, '⚠ Si cambiaste el tamaño de la ventana, recargá antes de auditar.', AVISO);

        r.forEach(function (g) {
            if (g.ok) return;
            seccion(p, '❌ ' + g.grafico, '#e17055');
            if (g.pisadas && g.pisadas.length) {
                nota(p, 'Se pisan:');
                tabla(p, g.pisadas, ['a', 'b', 'px']);
            }
            if (g.recortados && g.recortados.length) {
                nota(p, 'Cortados por el borde: ' + g.recortados.join(' · '));
            }
        });
        var sanos = r.filter(function (g) { return g.ok; });
        if (sanos.length) {
            seccion(p, 'Sin problemas', '#00b894');
            tabla(p, sanos.map(function (g) {
                return {grafico: g.grafico, textos: g.textos};
            }), ['grafico', 'textos']);
        }
    }

    // =====================================================================
    // RAYOS X — se mantiene encendido entre reruns leyendo su param
    // =====================================================================
    function pintarRayosX() {
        if (!cargarFuente('rayos_x', 'rayosX')) return;
        try { win.rayosX(); } catch (err) { console.warn('[herramientas] rayosX', err); }
    }
    function apagarRayosX() {
        if (win.rayosX) { try { win.rayosX({off: true}); } catch (err) {} }
    }

    // =====================================================================
    // BARRA
    // =====================================================================
    var ID_BARRA = 'herr-barra';

    // Cada modo declara como se lee y como se alterna. Inspector NO usa un
    // param propio: reusa el silenciador que inspector.py ya expone
    // (__inspectorTooltipSilenciado / __inspectorAlternarSilenciado), asi
    // apagarlo no apaga ?debug=1 — que es justamente lo que hace visible a
    // esta barra. Ver el acoplamiento en el docstring de herramientas.py.
    var MODOS = [
        {
            id: 'inspector', etiqueta: '🔍 Inspector',
            titulo: 'Tooltip con selectores, archivo:línea y estilos al pasar el cursor',
            leer: function () { return !win.__inspectorTooltipSilenciado; },
            alternar: function () {
                if (win.__inspectorAlternarSilenciado) win.__inspectorAlternarSilenciado();
            },
        },
        {
            id: 'diseno', etiqueta: '🎨 Diseño',
            titulo: 'Editar en vivo el elemento fijado (no persiste)',
            leer: function () { return activo('diseno'); },
            alternar: function () { fijar('diseno', !activo('diseno')); },
        },
        {
            id: 'rayosx', etiqueta: '🩻 Rayos X',
            titulo: 'Pinta la estructura: cajas en el flujo, escapados y pseudo-elementos',
            leer: function () { return activo('rayosx'); },
            alternar: function () {
                var nuevo = !activo('rayosx');
                fijar('rayosx', nuevo);
                if (nuevo) pintarRayosX(); else apagarRayosX();
            },
        },
    ];

    var ACCIONES = [
        {id: 'layout', etiqueta: '📐 Layout',
         titulo: 'Mide contenedores: desborde, alturas fuera de escala, holguras',
         correr: correrLayout},
        {id: 'graficos', etiqueta: '📊 Gráficos',
         titulo: 'Busca textos pisados o cortados en las figuras de Plotly',
         correr: correrGraficos},
    ];

    function estiloBoton(encendido) {
        return [
            'border:1px solid ' + (encendido ? ACENTO : BORDE),
            'background:' + (encendido ? ACENTO : 'transparent'),
            'color:' + (encendido ? '#fff' : TEXTO),
            'font:600 11px/1.3 -apple-system,sans-serif',
            'padding:4px 9px', 'border-radius:14px', 'cursor:pointer',
            'white-space:nowrap',
        ].join(';');
    }

    function construirBarra() {
        var vieja = doc.getElementById(ID_BARRA);
        if (vieja) vieja.remove();
        if (!barraVisible()) return;

        var barra = doc.createElement('div');
        barra.id = ID_BARRA;
        barra.style.cssText = [
            'position:fixed', 'left:72px', 'bottom:10px', 'z-index:2147483646',
            'display:flex', 'align-items:center', 'gap:6px', 'flex-wrap:wrap',
            'background:' + FONDO, 'border:1px solid ' + BORDE,
            'border-radius:18px', 'padding:5px 8px',
            'box-shadow:0 2px 10px rgba(0,0,0,.4)',
        ].join(';');

        MODOS.forEach(function (m) {
            var b = doc.createElement('button');
            b.textContent = m.etiqueta;
            b.title = m.titulo;
            b.style.cssText = estiloBoton(m.leer());
            b.addEventListener('click', function (ev) {
                ev.preventDefault(); ev.stopPropagation();
                m.alternar();
                construirBarra();
            });
            barra.appendChild(b);
        });

        var sep = doc.createElement('span');
        sep.style.cssText = 'width:1px;height:16px;background:' + BORDE + ';margin:0 2px';
        barra.appendChild(sep);

        ACCIONES.forEach(function (a) {
            var b = doc.createElement('button');
            b.textContent = a.etiqueta;
            b.title = a.titulo;
            b.style.cssText = estiloBoton(false);
            b.addEventListener('click', function (ev) {
                ev.preventDefault(); ev.stopPropagation();
                a.correr();
            });
            barra.appendChild(b);
        });

        // Aviso de modos que se estorban. No se bloquea la combinacion (el
        // usuario puede querer verla): se avisa, que es lo que faltaba
        // cuando esto costo una sesion entera de diagnostico.
        if (activo('diseno') && activo('rayosx')) {
            var av = doc.createElement('span');
            av.textContent = '⚠ Diseño mueve con transform: los recuadros de Rayos X salen corridos (regla #156)';
            av.style.cssText = 'color:' + AVISO + ';font:400 10px/1.3 -apple-system,sans-serif;'
                             + 'max-width:260px';
            barra.appendChild(av);
        }

        doc.body.appendChild(barra);
        apilarBadgeInspector(barra);
    }

    // El badge "Inspector ON" de inspector.py vivia en esta misma esquina.
    // Se lo sube JUSTO encima de la barra, midiendo: con una constante
    // coordinada a mano se superponian, porque el alto de la barra no es
    // fijo (crece cuando aparece el aviso de modos que se estorban, y con
    // flex-wrap puede pasar a dos filas). Ver el comentario gemelo en
    // _inspector_js.py, junto al cssText del badge.
    function apilarBadgeInspector(barra) {
        var badge = doc.getElementById('el-inspector-badge');
        if (!badge) return;
        var alto = Math.round(barra.getBoundingClientRect().height);
        badge.style.bottom = (10 + alto + 8) + 'px';
    }

    // ── arranque ─────────────────────────────────────────────────────────
    // Las fuentes se cargan siempre que la barra este visible (no al
    // clickear): asi `rayosX()`/`auditar()`/`auditarGraficos()` quedan
    // disponibles tambien para llamarlas a mano desde la consola, sin
    // pegar nada. Con ?debug=0 no se carga nada: coste cero en produccion.
    if (barraVisible()) {
        cargarFuente('rayos_x', 'rayosX');
        cargarFuente('auditar_layout', 'auditar');
        cargarFuente('auditar_graficos', 'auditarGraficos');
        construirBarra();
        // Rayos X se repinta en CADA ejecucion del script (o sea en cada
        // rerun de Streamlit): el DOM que media quedo obsoleto y los
        // recuadros habrian quedado sobre elementos que ya no estan.
        if (activo('rayosx')) pintarRayosX();
    } else {
        var b = doc.getElementById(ID_BARRA); if (b) b.remove();
        cerrarPanel();
        apagarRayosX();
    }

    // El Alt+I del inspector reescribe ?debug con replaceState, que NO
    // dispara popstate: sin este listener propio la barra quedaria colgada
    // en pantalla despues de salir con el atajo. Se reinstala en cada
    // ejecucion (el realm del iframe anterior murio) con el mismo patron
    // remove-old/add-new que usan inspector.py y diseno.py.
    if (win.__herramientasKeyHandler) {
        doc.removeEventListener('keydown', win.__herramientasKeyHandler, true);
    }
    win.__herramientasKeyHandler = function (e) {
        if (e.altKey && (e.key === 'i' || e.key === 'I')) {
            // Corre DESPUES del handler del inspector (que es quien
            // reescribe la URL); el setTimeout lo deja leer el estado ya
            // actualizado en vez del anterior.
            win.setTimeout(function () {
                construirBarra();
                if (!barraVisible()) { cerrarPanel(); apagarRayosX(); }
            }, 0);
        }
    };
    doc.addEventListener('keydown', win.__herramientasKeyHandler, true);
})();
</script>
"""
