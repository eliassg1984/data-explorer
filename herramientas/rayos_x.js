/**
 * rayos_x.js  —  ver la ESTRUCTURA de la página, no su pintura.
 *
 * Cómo usar:
 *   1. Levantar el preview (`streamlit run app.py` o `preview_start` name="app").
 *   2. Abrir DevTools (F12) → pestaña Console.
 *   3. Pegar todo este archivo y presionar Enter. Se define `rayosX()`.
 *   4. Llamar:
 *        rayosX()                      // encender / repintar
 *        rayosX({off: true})           // apagar
 *        rayosX({soloEscapados: true}) // solo lo que se despegó de su padre
 *        rayosX({key: 'fila_ajuste'})  // solo las keys que contengan ese texto
 *
 * POR QUÉ EXISTE (2026-08-22)
 * `auditar_layout.js` mide y reporta en TEXTO; el inspector (?debug=1) marca
 * UN elemento por vez. Ninguno responde la pregunta "¿qué caja es cada cosa
 * de las que veo?", que es justo la que se hace uno cuando una franja se ve
 * como una sola tira pero en el código son tres piezas independientes.
 *
 * Pinta tres cosas que a simple vista son indistinguibles:
 *
 *   ─ CAJAS EN EL FLUJO (línea llena, color por nivel de anidado). Están donde
 *     su padre las puso. Es el caso normal: mover el padre las mueve.
 *
 *   ─ ESCAPADOS (línea cortada + 🪂). Tienen position:fixed/absolute: viven
 *     dentro de un padre en el código pero se dibujan en coordenadas propias.
 *     Se les traza una LÍNEA hasta el padre al que pertenecen — esa línea es
 *     la respuesta visual a "¿de dónde salió esto?".
 *
 *   ─ PSEUDO-ELEMENTOS (línea de puntos, ::before/::after). No existen en el
 *     HTML: los inventa el CSS. Son los que pintan las bandas de color que
 *     uno busca en el árbol y no encuentra, porque no están ahí.
 *
 * Ojo con una trampa que este proyecto ya pisó: un `transform` en un ancestro
 * CAPTURA a sus hijos `fixed` (dejan de anclarse a la pantalla y pasan a
 * anclarse a él). Por eso las cajas de los escapados se calculan contra su
 * ancestro transformado si lo hay, y no contra el viewport. Sin eso, con el
 * modo diseño abierto los recuadros salen corridos.
 *
 * NO modifica la página: todo se dibuja en una capa aparte, encima y sin
 * capturar clics. Se va con rayosX({off:true}) o recargando.
 */
(function () {
  const ID_CAPA = 'rayos-x-capa';
  // Color por NIVEL de anidado (no por tipo): el mismo tono = la misma
  // profundidad, así el anidado se lee de un vistazo sin abrir el árbol.
  const PALETA = ['#6c5ce7', '#0984e3', '#00b894', '#e1a100', '#e17055', '#d63031'];
  const COLOR_ESCAPADO = '#e17055';
  const COLOR_PSEUDO = '#00b894';

  function quitar() {
    const previa = document.getElementById(ID_CAPA);
    if (previa) previa.remove();
  }

  // El ancestro que "captura" a un hijo fixed. Incluye al propio elemento
  // porque un ::before es hijo suyo: si el elemento tiene transform, su
  // pseudo se posiciona contra él, no contra la pantalla.
  function baseDeFixed(el) {
    let n = el;
    while (n && n !== document.documentElement) {
      const t = getComputedStyle(n).transform;
      if (t && t !== 'none') return n;
      n = n.parentElement;
    }
    return null;
  }

  function baseDeAbsolute(el) {
    let n = el.parentElement;
    while (n && n !== document.documentElement) {
      const cs = getComputedStyle(n);
      if (cs.position !== 'static' || (cs.transform && cs.transform !== 'none')) return n;
      n = n.parentElement;
    }
    return null;
  }

  function keyDe(el) {
    const m = (el.className || '').toString().match(/st-key-([\w-]+)/);
    return m ? m[1] : null;
  }

  // Nivel = cuántos contenedores CON KEY lo envuelven. Es el anidado que
  // importa acá; el del DOM crudo cuenta wrappers de Streamlit sin sentido.
  function nivelDe(el) {
    let n = 0, p = el.parentElement;
    while (p) {
      if (keyDe(p)) n++;
      p = p.parentElement;
    }
    return n;
  }

  // Caja de un pseudo-elemento. Solo se puede calcular si está posicionado
  // (fixed/absolute); los que fluyen no son medibles desde JS y además no
  // son los que confunden.
  function cajaPseudo(el, cual) {
    const cs = getComputedStyle(el, cual);
    const contenido = cs.content;
    if (!contenido || contenido === 'none' || contenido === 'normal') return null;

    const pinta = (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)')
               || parseFloat(cs.borderTopWidth) > 0
               || parseFloat(cs.borderBottomWidth) > 0
               || (contenido !== '""' && contenido !== "''");
    if (!pinta) return null;

    const pos = cs.position;
    if (pos !== 'fixed' && pos !== 'absolute') return null;

    const base = pos === 'fixed' ? baseDeFixed(el) : baseDeAbsolute(el);
    const rb = base ? base.getBoundingClientRect() : {left: 0, top: 0};
    const left = parseFloat(cs.left), top = parseFloat(cs.top);
    const w = parseFloat(cs.width), h = parseFloat(cs.height);
    if (!isFinite(left) || !isFinite(top) || !isFinite(w) || !isFinite(h)) return null;
    if (w < 2 || h < 2) return null;   // colapsado: no hay nada que mostrar

    return {left: rb.left + left, top: rb.top + top, width: w, height: h,
            capturadoPor: base ? (keyDe(base) || base.tagName.toLowerCase()) : null};
  }

  function marco(capa, caja, color, estilo, etiqueta, titulo) {
    const d = document.createElement('div');
    d.style.cssText = [
      'position:fixed',
      'left:' + caja.left + 'px', 'top:' + caja.top + 'px',
      'width:' + caja.width + 'px', 'height:' + caja.height + 'px',
      'border:1.5px ' + estilo + ' ' + color,
      'border-radius:2px',
      'box-sizing:border-box',
      'pointer-events:none',
    ].join(';');
    capa.appendChild(d);

    // La etiqueta solo si la caja da para leerla; si no, ensucia más de lo
    // que aclara (hay decenas de wrappers de pocos píxeles).
    if (etiqueta && caja.width > 55 && caja.height > 15) {
      const t = document.createElement('div');
      t.textContent = etiqueta;
      t.title = titulo || '';
      t.style.cssText = [
        'position:fixed',
        'left:' + caja.left + 'px',
        'top:' + Math.max(0, caja.top - 13) + 'px',
        'background:' + color, 'color:#fff',
        'font:600 9px/13px ui-monospace,Menlo,Consolas,monospace',
        'padding:0 4px', 'border-radius:2px 2px 0 0',
        'white-space:nowrap', 'pointer-events:none',
        'max-width:' + Math.max(60, caja.width) + 'px',
        'overflow:hidden', 'text-overflow:ellipsis',
      ].join(';');
      capa.appendChild(t);
    }
    return d;
  }

  window.rayosX = function (opts = {}) {
    const cfg = {off: false, soloEscapados: false, key: null, ...opts};
    quitar();
    if (cfg.off) { console.log('%c[rayos_x] apagado', 'color:#6c5ce7'); return; }

    const capa = document.createElement('div');
    capa.id = ID_CAPA;
    capa.style.cssText =
      'position:fixed;inset:0;z-index:2147483000;pointer-events:none';
    document.body.appendChild(capa);

    // Las líneas escapado→padre van en un SVG propio, encima de los marcos.
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('style',
      'position:fixed;inset:0;width:100%;height:100%;pointer-events:none');
    capa.appendChild(svg);

    const enFlujo = [], escapados = [], pseudos = [];

    document.querySelectorAll('[class*="st-key-"]').forEach(el => {
      const key = keyDe(el);
      if (!key) return;
      if (cfg.key && key.indexOf(cfg.key) === -1) return;

      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return;

      const cs = getComputedStyle(el);
      const pos = cs.position;
      const escapado = (pos === 'fixed' || pos === 'absolute');

      if (escapado) {
        // El padre con key al que pertenece EN EL CÓDIGO (no en la pantalla).
        let padre = el.parentElement, keyPadre = null;
        while (padre) { const k = keyDe(padre); if (k) { keyPadre = k; break; } padre = padre.parentElement; }
        escapados.push({key, pos, padre: keyPadre, el, r, padreEl: padre});
      } else if (!cfg.soloEscapados) {
        enFlujo.push({key, nivel: nivelDe(el), r});
      }

      if (!cfg.soloEscapados) {
        ['::before', '::after'].forEach(cual => {
          const caja = cajaPseudo(el, cual);
          if (caja) pseudos.push({key, cual, caja});
        });
      }
    });

    // ── pintar: flujo primero (queda debajo), escapados y pseudos encima ──
    enFlujo.forEach(c => {
      const color = PALETA[Math.min(c.nivel, PALETA.length - 1)];
      marco(capa, c.r, color, 'solid', c.key, `nivel ${c.nivel} · en el flujo`);
    });

    pseudos.forEach(p => {
      marco(capa, p.caja, COLOR_PSEUDO, 'dotted', p.key + p.cual,
            'pseudo-elemento: lo pinta el CSS, no existe en el HTML'
            + (p.caja.capturadoPor ? ` · capturado por ${p.caja.capturadoPor}` : ''));
    });

    escapados.forEach(e => {
      marco(capa, e.r, COLOR_ESCAPADO, 'dashed', '🪂 ' + e.key,
            `${e.pos} · vive dentro de ${e.padre || '(sin padre con key)'}`);
      // La línea hasta el padre del código: el "de dónde salió esto".
      if (e.padreEl) {
        const rp = e.padreEl.getBoundingClientRect();
        if (rp.width > 2 && rp.height > 2) {
          const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l.setAttribute('x1', e.r.left + e.r.width / 2);
          l.setAttribute('y1', e.r.top + e.r.height / 2);
          l.setAttribute('x2', rp.left + rp.width / 2);
          l.setAttribute('y2', rp.top + rp.height / 2);
          l.setAttribute('stroke', COLOR_ESCAPADO);
          l.setAttribute('stroke-width', '1');
          l.setAttribute('stroke-dasharray', '3 3');
          l.setAttribute('opacity', '0.55');
          svg.appendChild(l);
        }
      }
    });

    // ── leyenda ──
    const leyenda = document.createElement('div');
    leyenda.style.cssText = [
      'position:fixed', 'left:10px', 'bottom:10px', 'z-index:1',
      'background:#101014', 'color:#cfcfd6',
      'border:1px solid #2a2a35', 'border-radius:6px',
      'padding:8px 10px', 'font:11px/1.5 -apple-system,sans-serif',
      'pointer-events:none', 'box-shadow:0 2px 8px rgba(0,0,0,.35)',
    ].join(';');
    leyenda.innerHTML =
      '<b style="color:#fff">rayos X</b><br>' +
      `<span style="color:${PALETA[0]}">━</span> caja en el flujo ` +
      `<span style="opacity:.6">(color = nivel de anidado)</span><br>` +
      `<span style="color:${COLOR_ESCAPADO}">╌</span> 🪂 escapado ` +
      `<span style="opacity:.6">(la línea va a su padre del código)</span><br>` +
      `<span style="color:${COLOR_PSEUDO}">┈</span> pseudo-elemento ` +
      `<span style="opacity:.6">(lo pinta el CSS, no está en el HTML)</span><br>` +
      `<span style="opacity:.6">rayosX({off:true}) para apagar</span>`;
    capa.appendChild(leyenda);

    // Al scrollear los recuadros quedarían atrás: se repintan solos.
    const repintar = () => { if (document.getElementById(ID_CAPA)) window.rayosX(cfg); };
    addEventListener('scroll', repintar, {once: true, passive: true});
    addEventListener('resize', repintar, {once: true});

    console.log('%c[rayos_x]', 'color:#6c5ce7;font-weight:bold',
                `${enFlujo.length} en el flujo · ${escapados.length} escapados · `
              + `${pseudos.length} pseudo-elementos`);
    if (escapados.length) {
      console.log('Escapados (se dibujan lejos de donde viven en el código):');
      console.table(escapados.map(e => ({
        key: e.key, position: e.pos, viveDentroDe: e.padre,
        top: Math.round(e.r.top), left: Math.round(e.r.left),
      })));
    }
    if (pseudos.length) {
      console.log('Pseudo-elementos que pintan (no existen en el HTML):');
      console.table(pseudos.map(p => ({
        elemento: p.key + p.cual,
        w: Math.round(p.caja.width), h: Math.round(p.caja.height),
        capturadoPor: p.caja.capturadoPor,
      })));
    }
    return {enFlujo: enFlujo.length, escapados, pseudos};
  };

  console.log('%crayosX()%c disponible. Ejemplos:\n' +
              '  rayosX()\n  rayosX({soloEscapados:true})\n' +
              "  rayosX({key:'fila_ajuste'})\n  rayosX({off:true})",
              'color:#6c5ce7;font-weight:bold', 'color:inherit');
})();
