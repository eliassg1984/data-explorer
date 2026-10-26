/* Balance en soles del mismo cierre y productos de Destino. Sin consultas ni
   escrituras: la simulación trabaja sobre copias de los nodos agregados. */
const DESTINO_FLUJO = (() => {
  const EPS = 1e-7;
  const numero = x => Number.isFinite(Number(x)) ? Number(x) : 0;
  const suma = (rs, f) => rs.reduce((a, r) => a + f(r), 0);
  const grupos = {
    plato: 'A un plato', prep: 'En preparaciones', notas: 'Notas de salida',
    conteo: 'Ajustes al contar', otros: 'Otros movimientos', stock: 'Stock final',
    valorizacion: 'Valorización / conciliación', producido: 'Ingresos de producción'
  };
  const colores = {plato: 'venta', prep: 'prep', notas: 'baja', conteo: 'falt',
    otros: 'otros_mov', stock: 'stock', valorizacion: 'valorizacion', producido: 'prep'};
  const dinero = x => 'S/ ' + numero(x).toLocaleString('es-PE', {maximumFractionDigits: 2});
  const esc = x => String(x ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  function aportes(r) {
    const a = [];
    function agregar(parte, nombre, grupo, lado, valor, codigo = '', color = null) {
      valor = numero(valor);
      if (Math.abs(valor) <= EPS) return;
      const reverso = valor < 0;
      const side = reverso ? (lado === 'in' ? 'out' : 'in') : lado;
      const label = reverso ? (['ini', 'fin'].includes(parte) ? nombre + ' negativo' : 'Reverso: ' + nombre.toLowerCase()) : nombre;
      a.push({id: side + ':' + parte, parte, grupo, side, label, value: Math.abs(valor),
        codigo, color: color || colores[grupo] || 'venta', reverso});
    }
    agregar('ini', 'Stock inicial', 'origen', 'in', r.ini_v);
    agregar('compra', 'Compras netas', 'origen', 'in', r.compra_v, 'SUNAT < 90');
    const tipos = [['94', 'Orden de producción'], ['96', 'Porcionamiento'], ['90', 'Empacado']];
    const desglosado = tipos.every(([t]) => Number.isFinite(r['prep_' + t + '_v']) && Number.isFinite(r['ing_' + t + '_v']));
    if (desglosado) {
      for (const [t, nombre] of tipos) {
        agregar('ing' + t, 'Ingreso: ' + nombre.toLowerCase(), 'producido', 'in', r['ing_' + t + '_v'], t);
        agregar('prep' + t, nombre, 'prep', 'out', r['prep_' + t + '_v'], t);
      }
    } else {
      agregar('producido', 'Ingresos de producción', 'producido', 'in', numero(r.entro_v) - numero(r.compra_v), '90 / 94 / 96');
      agregar('prep', 'En preparaciones', 'prep', 'out', r.prep_v, '90 / 94 / 96 · Sin desglose');
    }
    agregar('venta', 'Venta, incluidos combos', 'plato', 'out', r.venta_v, '95', 'venta');
    agregar('cort', 'Cortesías', 'plato', 'out', r.cort_v, '95', 'cort');
    agregar('evvi', 'Eventos y venta interna', 'plato', 'out', r.evvi_v, '95', 'evvi');
    agregar('baja', 'Bajas', 'notas', 'out', r.baja_v, '98 · Bajas', 'baja');
    if (['91', '92', '98'].every(t => Number.isFinite(r['nota_' + t + '_v']))) {
      agregar('nota91', 'Control interno', 'notas', 'out', r.nota_91_v, '91', 'otras');
      agregar('nota92', 'Merma fija', 'notas', 'out', r.nota_92_v, '92', 'otras');
      const resto98 = r.nota_98_v - numero(r.baja_v);
      if (resto98 < -EPS && numero(r.baja_v) > EPS) {
        agregar('conciliacion_notas', 'Diferencia bajas / notas 98', 'valorizacion', 'in', -resto98,
          'Salidas vs kardex · conciliación de fuentes');
      } else {
        agregar('nota98', 'Otras notas', 'notas', 'out', resto98, '98 · Personal, uso del área y otros', 'otras');
      }
    } else {
      agregar('otras', 'Otras salidas', 'notas', 'out', r.otras_v, '91 / 92 / 98 · Sin desglose', 'otras');
    }
    const ajuste = numero(r.aj_v);
    agregar('sobr', 'Ajuste positivo', 'origen', 'in', Math.max(0, ajuste), '93', 'sobr');
    const operacion = r.clase === 'operacion';
    agregar(operacion ? 'operacion' : 'falt', operacion ? 'Consumido al contar' : 'Faltante',
      'conteo', 'out', Math.max(0, -ajuste), '93 · ' + (operacion ? 'Insumos de operación' : 'Alimentos y bebidas'), 'falt');
    agregar('otros_ing', 'Otros ingresos', 'otros', 'in', r.otros_ing_v, 'Tipos no clasificados');
    agregar('otros_sal', 'Otras salidas del kardex', 'otros', 'out', r.otros_sal_v, 'Tipos no clasificados');
    agregar('fin', 'Stock final', 'stock', 'out', r.fin_v);
    // El saldo contado se conserva. Las diferencias de precio o de fuentes
    // no se convierten en faltante ni en una salida ficticia del producto.
    const diferencia = suma(a, n => (n.side === 'in' ? 1 : -1) * n.value);
    if (Math.abs(diferencia) > EPS) {
      const side = diferencia > 0 ? 'out' : 'in';
      a.push({id: side + ':valorizacion', parte: 'valorizacion', grupo: 'valorizacion', side,
        label: 'Valorización / conciliación ' + (side === 'in' ? '(+)' : '(−)'),
        value: Math.abs(diferencia), codigo: 'Diferencia del balance en soles', color: 'valorizacion'});
    }
    return a;
  }

  function agrupar(nodos, modo) {
    if (modo === 'detalle') return nodos.map(n => ({...n, hojas: [n.id]}));
    const m = new Map();
    for (const n of nodos) {
      const agrupa = n.side === 'out' && !n.reverso && grupos[n.grupo] && n.grupo !== 'valorizacion' || n.side === 'in' && n.grupo === 'producido' && !n.reverso;
      const id = agrupa ? n.side + ':grupo:' + n.grupo : n.id;
      if (!m.has(id)) m.set(id, {...n, id, label: agrupa ? grupos[n.grupo] : n.label,
        color: agrupa ? colores[n.grupo] : n.color, hojas: [] , value: 0});
      const t = m.get(id); t.value += n.value; t.hojas.push(n.id);
    }
    return [...m.values()];
  }

  function modelo(rows, modo = 'resumen', cambios = null) {
    const m = new Map();
    for (const r of rows) for (const n of aportes(r)) {
      if (!m.has(n.id)) m.set(n.id, {...n, value: 0});
      m.get(n.id).value += n.value;
    }
    let hojas = [...m.values()];
    if (cambios) {
      hojas = hojas.filter(n => n.parte !== 'fin').map(n => ({...n,
        value: n.parte !== 'valorizacion' && Object.hasOwn(cambios, n.id) && Number.isFinite(cambios[n.id]) && cambios[n.id] >= 0 ? cambios[n.id] : n.value}));
      const saldo = suma(hojas, n => (n.side === 'in' ? 1 : -1) * n.value);
      if (Math.abs(saldo) > EPS) hojas.push({id: (saldo >= 0 ? 'out' : 'in') + ':fin', parte: 'fin', grupo: 'stock', side: saldo >= 0 ? 'out' : 'in',
        label: saldo >= 0 ? 'Stock final simulado' : 'Stock final simulado negativo', value: Math.abs(saldo), codigo: 'Saldo calculado del escenario', color: 'stock', reverso: saldo < 0});
    }
    const nodos = agrupar(hojas.filter(n => n.value > EPS), modo);
    const ordenSalida = ['plato', 'prep', 'notas', 'conteo', 'otros', 'stock', 'valorizacion'];
    const prioridad = n => n.side === 'out' ? (ordenSalida.indexOf(n.grupo) < 0 ? 8 : ordenSalida.indexOf(n.grupo))
      : n.parte === 'compra' ? 0 : n.parte === 'ini' ? 1 : n.grupo === 'producido' ? 2 : n.parte === 'sobr' ? 3 : 4;
    nodos.sort((a, b) => prioridad(a) - prioridad(b));
    const stock = suma(hojas.filter(n => n.parte === 'fin'), n => (n.side === 'out' ? 1 : -1) * n.value);
    const compras = suma(hojas.filter(n => n.parte === 'compra'), n => (n.side === 'in' ? 1 : -1) * n.value);
    const entradas = suma(hojas.filter(n => n.side === 'in'), n => n.value);
    const salidas = suma(hojas.filter(n => n.side === 'out'), n => n.value);
    return {hojas, nodos, entradas, salidas, stock, compras, diferencia: entradas - salidas, simulado: !!cambios};
  }

  function contribucion(r, id) {
    const [side, tipo, grupo] = String(id).split(':');
    return suma(aportes(r).filter(n => tipo === 'grupo' ? n.side === side && n.grupo === grupo && !n.reverso : n.id === id), n => n.value);
  }

  function estado(s) {
    if (!s || typeof s !== 'object' || Array.isArray(s)) s = {};
    return {modo: s.modo === 'detalle' ? 'detalle' : 'resumen', ambito: s.ambito === 'producto' ? 'producto' : 'visibles',
      destino: typeof s.destino === 'string' ? s.destino : '', simular: s.simular === true,
      cambios: s.cambios && typeof s.cambios === 'object' && !Array.isArray(s.cambios) ? s.cambios : {}, contexto: typeof s.contexto === 'string' ? s.contexto : ''};
  }

  function montar(host, opciones) {
    const abort = new AbortController(), doc = host.ownerDocument;
    let real, mostrado, contexto, rows = [], producto, ancho = 0;
    const get = () => opciones.estado();
    const color = k => opciones.colores[k] || opciones.colores.otras;
    host.innerHTML = `<div class="dstf-head"><div><h3>Destino del inventario</h3><p class="dst-ayuda">Balance en S/ al costo · los mismos productos y cierre de la vista</p></div><div class="dstf-controls"><select data-flujo="ambito" aria-label="Ámbito del Sankey"><option value="visibles">Productos visibles</option><option value="producto">Producto elegido</option></select><div role="group" aria-label="Detalle del Sankey"><button type="button" data-flujo="resumen">Resumen</button><button type="button" data-flujo="detalle">Desglose</button></div><label><input type="checkbox" data-flujo="simular"> Simular escenario</label></div></div><div class="dstf-metrics" aria-live="polite"></div><div class="dstf-grid"><div class="dstf-canvas"><svg class="dstf-svg" role="img" aria-label="Sankey del balance de inventario"></svg><div class="dstf-nodos"></div></div><section class="dstf-editor" aria-label="Detalle del nodo seleccionado"><div class="dstf-editor-content"></div></section></div><div class="dstf-seleccion" aria-live="polite"></div><details class="dstf-metodo"><summary>Cuenta y movimientos internos</summary><p>Stock inicial + compras netas + ingresos de producción + ajustes positivos = destinos + stock final. Los códigos 97 (transferencias) y 99 (requerimientos) se compensan entre áreas y quedan fuera del consumo del restaurante.</p><p>Las ventas incluyen combos; cortesías y eventos/venta interna son partes del descargo 95. El consumo al contar de insumos de operación se separa del faltante de alimentos. Producción transforma el valor, no es pérdida.</p><p>Valorización / conciliación es la diferencia entre movimientos valorizados y existencias del kardex. Puede incluir cambios de precio o diferencias entre fuentes; no se atribuye a pérdida. Las devoluciones y stocks negativos se muestran con su signo mediante nodos en el lado contrario.</p><p>Este balance no asigna una factura de compra a una venta concreta. Siempre se muestra en soles; las unidades de la tabla mantienen su propio selector.</p></details>`;
    const $ = q => host.querySelector(q);
    const svg = $('.dstf-svg'), layer = $('.dstf-nodos');

    function elegir(id) { get().destino = get().destino === id ? '' : id; opciones.cambiar(true); }
    function metricas() {
      $('.dstf-metrics').innerHTML = `<div><span>Compras netas</span><strong>${dinero(mostrado.compras)}</strong></div><div><span>Entradas del balance</span><strong>${dinero(mostrado.entradas)}</strong></div><div><span>Stock final ${get().simular ? 'simulado' : 'del kardex'}</span><strong>${dinero(mostrado.stock)}</strong></div><p class="${get().simular ? 'dstf-aviso' : ''}">${get().simular ? 'SIMULACIÓN · Tabla y ficha: datos reales. Escenario: sólo este Sankey.' : 'DATOS REALES · ' + (get().ambito === 'producto' ? (producto ? 1 : 0) : rows.length) + ' productos · ' + esc(contexto.nombre)}</p>`;
    }
    function seleccionado() {
      const actual = mostrado.nodos.find(n => n.id === get().destino);
      if (actual || !get().simular) return actual;
      const original = real.nodos.find(n => n.id === get().destino);
      return original ? {...original, value: suma(mostrado.hojas.filter(n => original.hojas.includes(n.id)), n => n.value)} : null;
    }
    function editor() {
      const s = get(), nodo = seleccionado();
      const campos = nodo ? mostrado.hojas.filter(n => nodo.hojas.includes(n.id)) : [];
      $('.dstf-editor-content').innerHTML = `<div class="dstf-tag">${s.simular ? 'ESCENARIO EDITABLE' : 'DETALLE REAL'}</div><h3>${esc(nodo?.label || 'Explora el flujo')}</h3><p class="dst-ayuda">${s.ambito === 'producto' && producto ? esc(producto.producto) : 'Los productos visibles de este cierre'}</p>${nodo ? `<strong class="dstf-valor">${dinero(nodo.value)}</strong>${campos.map(n => `<div class="dstf-campo"><label for="dstf-${esc(n.id)}">${esc(n.label)}<small>${esc(n.codigo)}</small></label>${s.simular && !['fin', 'valorizacion'].includes(n.parte) ? `<input type="number" id="dstf-${esc(n.id)}" data-flujo-importe="${esc(n.id)}" aria-label="${esc(n.label)}, importe simulado en soles" min="0" max="1000000000000" step="any" value="${n.value}">` : `<span>${dinero(n.value)}</span>`}</div>`).join('')}` : '<p class="dst-ayuda">Selecciona un origen o destino para ver su composición y los productos que contribuyen.</p>'}<p class="dstf-validacion" role="status" aria-live="polite"></p>${s.simular ? '<button type="button" data-flujo="restablecer">Restablecer escenario</button><p class="dst-ayuda">El stock se recalcula. La diferencia de valorización real se conserva como supuesto.</p>' : '<p class="dst-ayuda">Activa «Simular escenario» para probar importes sobre una copia.</p>'}`;
      validar();
    }
    function validar() {
      const aviso = $('.dstf-validacion');
      aviso.classList.toggle('dstf-error', mostrado.stock < -EPS);
      aviso.textContent = mostrado.stock < -EPS ? 'Stock negativo: ' + dinero(mostrado.stock) + '. Revisa entradas y destinos.' : 'Stock final: ' + dinero(mostrado.stock);
    }
    function seleccion() {
      const nodo = seleccionado();
      $('.dstf-seleccion').innerHTML = nodo ? `Detalle de productos: <b>${esc(nodo.label)}</b> <button type="button" data-flujo="limpiar">Quitar selección</button>` : 'Elige un nodo para filtrar el detalle de productos.';
    }
    function dibujar() {
      if (!mostrado) return;
      const w = $('.dstf-canvas').clientWidth;
      if (!w) return;
      ancho = w;
      const s = get(), izq = mostrado.nodos.filter(n => n.side === 'in'), der = mostrado.nodos.filter(n => n.side === 'out');
      svg.replaceChildren(); layer.replaceChildren();
      const ns = 'http://www.w3.org/2000/svg';
      function e(t, a, text) { const n = doc.createElementNS(ns, t); for (const [k, v] of Object.entries(a || {})) n.setAttribute(k, String(v)); if (text !== undefined) n.textContent = text; return n; }
      const h = Math.max(385, Math.max(izq.length, der.length) * 55 + 180), top = 48, bottom = 24, gap = 55;
      svg.setAttribute('viewBox', `0 0 ${w} ${h}`); svg.style.height = h + 'px';
      svg.append(e('title', {}, 'Origen y destino del inventario, al costo'));
      svg.append(e('desc', {}, (s.simular ? 'Simulación. ' : 'Datos reales. ') + 'Entradas ' + dinero(mostrado.entradas) + '. Stock final ' + dinero(mostrado.stock)));
      if (!izq.length && !der.length) { svg.append(e('text', {x: 12, y: 75}, 'Sin movimientos valorizados con estos filtros.')); return; }
      const maxL = Math.max(izq.length, der.length), escala = mostrado.entradas > EPS ? Math.max(80, h - top - bottom - gap * (maxL - 1)) / mostrado.entradas : 0;
      const labelW = w < 420 ? 116 : 142, x1 = 8, x3 = Math.max(90, w - labelW - 14), x2 = (x1 + x3) / 2, bar = 8;
      const poolH = mostrado.entradas * escala, poolY = top + (h - top - bottom - poolH) / 2;
      svg.append(e('text', {x: x1, y: 18, class: 'dstf-etiqueta'}, 'ORIGEN'));
      svg.append(e('text', {x: x3, y: 18, class: 'dstf-etiqueta'}, 'DESTINO'));
      if (w >= 420) svg.append(e('text', {x: x2, y: poolY - 12, 'text-anchor': 'middle', class: 'dstf-etiqueta'}, 'Balance'));
      function link(x, y, xx, yy, alto, n) {
        const c = (x + xx) / 2, path = e('path', {d: `M${x},${y} C${c},${y} ${c},${yy} ${xx},${yy} L${xx},${yy + alto} C${c},${yy + alto} ${c},${y + alto} ${x},${y + alto} Z`, fill: color(n.color), opacity: !s.destino || n.id === s.destino ? .3 : .08});
        path.append(e('title', {}, n.label + ': ' + dinero(n.value))); svg.append(path);
      }
      function columna(ns0, side) {
        const espaciado = ns0.length > 1 ? (h - top - bottom - poolH) / (ns0.length - 1) : 0;
        let y = ns0.length > 1 ? top : poolY, offset = 0;
        for (const n of ns0) {
          const alto = n.value * escala;
          if (side === 'in') link(x1 + bar, y, x2, poolY + offset, alto, n);
          else link(x2 + bar, poolY + offset, x3, y, alto, n);
          svg.append(e('rect', {x: side === 'in' ? x1 : x3, y, width: bar, height: Math.max(.5, alto), fill: color(n.color)}));
          const btn = doc.createElement('button'); btn.type = 'button'; btn.className = 'dstf-nodo'; btn.dataset.flujoNodo = n.id;
          btn.style.left = (side === 'in' ? x1 + 12 : x3 + 12) + 'px';
          btn.style.width = (side === 'in' ? Math.max(62, x2 - 22) : labelW) + 'px';
          btn.style.top = Math.max(27, Math.min(h - 48, y + alto / 2 - 24)) + 'px';
          btn.setAttribute('aria-pressed', String(s.destino === n.id));
          btn.setAttribute('aria-label', n.label + ', ' + dinero(n.value) + '. Ver detalle');
          btn.title = n.label;
          btn.innerHTML = `<span>${esc(n.label)}</span><small>${dinero(n.value)}</small>`; layer.append(btn);
          y += alto + espaciado; offset += alto;
        }
      }
      columna(izq, 'in'); columna(der, 'out');
      svg.append(e('rect', {x: x2, y: poolY, width: bar, height: Math.max(.5, poolH), fill: color('venta')}));
    }
    function actualizar(base, foco, periodo) {
      rows = base; producto = foco; contexto = periodo;
      const s = get(), alcance = s.ambito === 'producto' ? (foco ? [foco] : []) : base;
      const clave = periodo.clave + '|' + (periodo.sello || '') + '|' + s.ambito + '|' + JSON.stringify(alcance.map(r => [r.i, r.cod, r.unidad]));
      if (s.contexto !== clave) { s.cambios = {}; s.contexto = clave; }
      real = modelo(alcance, s.modo); mostrado = s.simular ? modelo(alcance, s.modo, s.cambios) : real;
      $('[data-flujo=ambito]').value = s.ambito; $('[data-flujo=simular]').checked = s.simular;
      for (const modo of ['resumen', 'detalle']) { const b = $('[data-flujo=' + modo + ']'); b.classList.toggle('on', s.modo === modo); b.setAttribute('aria-pressed', String(s.modo === modo)); }
      metricas(); editor(); seleccion(); dibujar();
    }
    host.addEventListener('click', event => {
      const button = event.composedPath().find(e => e?.dataset?.flujoNodo || e?.dataset?.flujo);
      if (!button || !host.contains(button) || button.tagName !== 'BUTTON') return;
      if (button.dataset.flujoNodo) { elegir(button.dataset.flujoNodo); return; }
      const accion = button.dataset.flujo, s = get();
      if (['resumen', 'detalle'].includes(accion)) { s.modo = accion; s.destino = ''; }
      else if (accion === 'limpiar') s.destino = '';
      else if (accion === 'restablecer') s.cambios = {};
      else return;
      opciones.cambiar(true);
    }, {signal: abort.signal});
    host.addEventListener('change', event => {
      const s = get();
      if (event.target.dataset.flujo === 'ambito') { s.ambito = event.target.value; s.destino = ''; opciones.cambiar(true); }
      if (event.target.dataset.flujo === 'simular') { s.simular = event.target.checked; opciones.cambiar(true); }
    }, {signal: abort.signal});
    host.addEventListener('input', event => {
      const input = event.target, id = input.dataset.flujoImporte;
      if (!id || !get().simular) return;
      const aviso = $('.dstf-validacion');
      if (!input.value || !input.validity.valid || !Number.isFinite(Number(input.value))) { input.setAttribute('aria-invalid', 'true'); aviso.classList.add('dstf-error'); aviso.textContent = 'Ingresa un importe válido mayor o igual a cero.'; return; }
      input.removeAttribute('aria-invalid'); get().cambios[id] = Number(input.value);
      const alcance = get().ambito === 'producto' ? (producto ? [producto] : []) : rows;
      mostrado = modelo(alcance, get().modo, get().cambios);
      const n = seleccionado();
      const valor = $('.dstf-valor'); if (valor && n) valor.textContent = dinero(n.value);
      metricas(); validar(); dibujar(); opciones.cambiar(false);
    }, {signal: abort.signal});
    const resize = new ResizeObserver(() => { if ($('.dstf-canvas').clientWidth !== ancho) dibujar(); }); resize.observe($('.dstf-canvas'));
    return {actualizar, get real() { return real; }, get mostrado() { return mostrado; }, cleanup() { abort.abort(); resize.disconnect(); }};
  }
  return {aportes, modelo, contribucion, estado, montar};
})();
window.__destinoFlujoDatos = DESTINO_FLUJO;
