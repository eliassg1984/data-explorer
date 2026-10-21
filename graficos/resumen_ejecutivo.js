// Portada mensual. Arriba, lo que entra en una pantalla de laptop (6
// indicadores, la venta del mes y las señales); abajo, el costo por familia,
// la conciliación y el método. Sólo el cambio de mes pide datos a Python.
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const valido = v => v != null && Number.isFinite(v);
const num = (v, dec = 0) => valido(v) ? v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec}) : '—';
const soles = (v, dec = 0) => valido(v) ? `${v < 0 ? '−' : ''}S/ ${num(Math.abs(v), dec)}` : '—';
const pct = v => valido(v) ? `${num(v * 100, 1)}%` : '—';
const signo = v => v >= 0 ? '+' : '−';
const pp = v => valido(v) ? `${signo(v)}${num(Math.abs(v) * 100, 1)} pp` : '—';
const varp = v => valido(v) ? `${signo(v)}${pct(Math.abs(v))}` : '—';
const variacion = (a, b) => valido(a) && valido(b) && b > 0 ? (a - b) / b : null;
const fecha = s => s ? s.split('-').reverse().join('/') : '';
const abrir = (url, texto) => `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(texto)}, abre en otra pestaña">${esc(texto)} ↗</a>`;

// Un cambio se pinta por lo que SIGNIFICA: en costo y descuentos, subir es malo.
function delta(v, base, {inverso = false, puntos = false} = {}) {
  if (!valido(v)) return '<span>Sin base comparable</span>';
  const clase = Math.abs(v) < 1e-9 ? '' : ((inverso ? v < 0 : v > 0) ? 'good' : 'bad');
  return `<span class="re-delta ${clase}">${esc(puntos ? pp(v) : varp(v))}</span> ${esc(base)}`;
}

function kpi(label, value, context, tip) {
  return `<section class="re-kpi" title="${esc(tip)}"><div class="re-label">${esc(label)}</div><div class="re-value">${esc(value)}</div><div class="re-context">${context}</div></section>`;
}

function kpis(d) {
  const a = d.actual, b = d.anterior, c = d.costo;
  const ap = b ? `vs ${d.anterior_corto}` : '';
  const mp = `vs ${d.previo_corto}`;
  const sinCierre = d.parcial ? '<span>Al cerrar el mes</span>' : '<span>Sin cierre comparable</span>';
  const descCtx = valido(a?.pct_descuento)
    ? `${esc(pct(a.pct_descuento))} de la carta${b && valido(b.pct_descuento) ? ` · ${delta(a.pct_descuento - b.pct_descuento, '', {inverso: true, puntos: true})}` : ''}`
    : '<span>Sin dato</span>';
  return [
    kpi('Venta neta', soles(a?.venta), delta(variacion(a?.venta, b?.venta), ap),
      'Todos los grupos de Ventas, por día del turno del comprobante; pagados y por cobrar, menos notas de crédito; sin IGV ni recargo.'),
    kpi('Clientes', num(a?.clientes), delta(variacion(a?.clientes, b?.clientes), ap),
      `Adultos, una vez por pedido; una nota de crédito resta. ${valido(a?.pedidos) ? `${num(a.pedidos)} pedidos en el período.` : ''}`),
    kpi('Ticket por cliente', soles(a?.ticket, 2), delta(variacion(a?.ticket, b?.ticket), ap),
      'Venta neta de los canales que registran clientes ÷ clientes: el «Ticket Pro.» de la Liquidación de Cajero. Rappi vende sin clientes y no entra.'),
    kpi('Descuentos', soles(a?.descuentos), descCtx,
      'Lo que se dejó de cobrar sobre el precio de carta, con impuestos, como «Descuentos» de Ventas › Resumen. El cambio es en puntos del % sobre la carta.'),
    kpi('Costo real', pct(c?.porcentaje), c ? delta(d.cambio_costo, mp, {inverso: true, puntos: true}) : sinCierre,
      'Consumo según inventario: inicial + compras − final, sobre la venta de Costos (Alimentos, Bebidas, Vinos y Envases; con Eventos, sin Venta interna).'),
    kpi('Costo del Sistema', pct(c?.porcentaje_pos), c ? delta(d.cambio_pos, mp, {inverso: true, puntos: true}) : sinCierre,
      'Costo histórico de lo vendido según las recetas del POS, sobre la misma venta de Costos. La distancia con el costo real es lo que explica la conciliación.'),
  ].join('');
}

function senal(clase, simbolo, titulo, detalle, link, texto) {
  return `<div class="re-signal"><span class="re-symbol ${clase}" aria-hidden="true">${simbolo}</span><div><strong>${titulo}</strong><p>${detalle}</p>${abrir(link, texto)}</div></div>`;
}

// Las señales van por importancia y no repiten un número sin agregarle algo:
// una buena noticia que no pide nada ya está en su indicador.
function alertas(d) {
  const a = d.actual, b = d.anterior, c = d.costo, out = [];
  const v = variacion(a?.venta, b?.venta);
  if (valido(v)) {
    const vc = variacion(a?.clientes, b?.clientes), vt = variacion(a?.ticket, b?.ticket);
    const causa = valido(vc) && valido(vt) ? `Clientes ${varp(vc)} · ticket ${varp(vt)}. ` : '';
    out.push(senal(v >= 0 ? 'good' : 'bad', v >= 0 ? '▲' : '▼',
      `La venta ${v >= 0 ? 'crece' : 'cae'} ${esc(pct(Math.abs(v)))} frente a ${esc(d.anterior_corto)} <span class="amount">${esc(soles(a.venta - b.venta))}</span>`,
      `${esc(causa)}${d.parcial ? 'Mismo tramo' : 'Mismas fechas'}: ${fecha(d.ini)} – ${fecha(d.fin)}.`, d.links.ventas, 'Abrir ventas'));
  }
  if (c && Math.abs(c.faltante) > 0.5) out.push(senal(c.faltante > 0 ? 'warn' : '', '!',
    `${esc(soles(c.faltante))} de costo sin explicar <span class="amount">${esc(pct(c.porcentaje_faltante))} de la venta</span>`,
    `Consumo carta ${esc(soles(c.carta))} contra Sistema ${esc(soles(c.pos))}, ya restadas las bajas (${esc(soles(c.bajas))}).`,
    d.links.costos, 'Ver la conciliación'));
  if (c && valido(d.cambio_costo) && d.cambio_costo >= 0.005) out.push(senal('bad', '▲',
    `El costo real subió ${esc(pp(d.cambio_costo))} frente a ${esc(d.previo_corto)}`,
    'Comparación entre meses cerrados y con la misma venta de Costos.', d.links.costos, 'Revisar costos'));
  if (a && b && valido(a.pct_descuento) && valido(b.pct_descuento) && a.pct_descuento - b.pct_descuento >= 0.01) out.push(senal('bad', '▲',
    `Los descuentos suben a ${esc(pct(a.pct_descuento))} de la carta`,
    `${esc(pp(a.pct_descuento - b.pct_descuento))} frente a ${esc(d.anterior_corto)} · ${esc(soles(a.descuentos))} en el período.`, d.links.ventas, 'Abrir ventas'));
  if (a && valido(a.sin_costo_pct) && a.sin_costo_pct >= 0.005) {
    const top = (a.sin_costo_top || []).map(x => x.plato), resto = (a.sin_costo_n || 0) - top.length;
    out.push(senal('warn', '!',
      `${esc(soles(a.sin_costo))} vendidos sin costo en el POS <span class="amount">${esc(pct(a.sin_costo_pct))} de la venta</span>`,
      `${top.length ? `${esc(top.join(', '))}${resto > 0 ? ` y ${resto} más` : ''}. ` : ''}Bajan el costo del Sistema.`, d.links.platos, 'Revisar platos'));
  }
  const n = (c?.observaciones?.detalle || []).length;
  if (n) out.push(senal('warn', '!', `${n} líneas de inventario con observaciones`,
    'Stock a precio cero, negativos o áreas que faltan en el cierre: revisarlas antes de leer el costo real.', d.links.costos, 'Ver observaciones'));
  return out.slice(0, 4).join('') || '<p class="muted">Nada que revisar con los datos de este período.</p>';
}

function familias(d) {
  const c = d.costo;
  if (!c) return `<div class="re-empty">${esc(d.error_costos || (d.parcial ? 'Mes en curso: el costo por familia estará cuando existan sus cierres.' : 'Sin dos cierres consecutivos para calcular este mes.'))}</div>`;
  const max = Math.max(1, ...c.familias.map(f => Math.abs(f.operativo)));
  const filas = c.familias.map(f => {
    const pos = f.venta_base > 0 ? f.pos / f.venta_base : null;
    return `<div class="re-fila"><span>${esc(f.familia)}</span><div class="re-track"><div class="re-bar ${f.familia.toLowerCase()}" style="width:${Math.min(100, Math.abs(f.operativo) / max * 100)}%"></div></div><b class="num">${pct(f.porcentaje)}</b><span class="num muted">${pct(pos)}</span><span class="num re-small">${soles(f.operativo)}</span></div>`;
  }).join('');
  return `<div class="re-fila re-fila-cab"><span></span><span></span><span class="num">Real</span><span class="num">Sistema</span><span class="num">Consumo</span></div>${filas}
    <p class="re-small">Venta de Costos: ${soles(c.venta_base)}. Incluye Eventos, sin Venta interna. Envases no tiene venta propia.</p>`;
}

function conciliacion(d) {
  const c = d.costo;
  if (!c) return '<div class="re-empty">La conciliación requiere el consumo mensual del período.</div>';
  const fila = (label, v, cl = '') => `<div class="re-ledger-row ${cl}"><span>${esc(label)}</span><b>${soles(v)}</b></div>`;
  return `<div class="re-ledger">${fila('Consumo real (inventario)', c.operativo)}${fila('− Consumos no vendidos', c.no_vendido)}${fila('= Consumo carta', c.carta, 'total')}${fila('− Costo del Sistema', c.pos)}${fila('= Diferencia', c.diferencia, 'total')}${fila('− Bajas registradas', c.bajas)}${fila('= Sin explicar', c.faltante, 'total')}</div>
    <p class="re-small">Los consumos no vendidos son cortesías y salidas que no son bajas. Los descuentos no entran en esta cuenta.</p>`;
}

function metodo(raiz) {
  return `<details class="re-method" ${raiz.__contextoAbierto ? 'open' : ''}><summary>Qué se cuenta y cómo se calcula</summary><div class="re-method-body">
      <section><h2>Venta neta</h2><p>Comprobantes pagados y por cobrar, menos notas de crédito, de todos los grupos; sin IGV ni recargo. Cada ítem se suma una vez aunque tenga varios pagos. El período usa el día del turno de caja.</p><p><strong>En Inforest:</strong> Registro de Ventas, con los mismos comprobantes y criterio de fecha.</p></section>
      <section><h2>Clientes, ticket y descuentos</h2><p>Clientes son adultos, una vez por pedido. El ticket es la venta de los canales que registran clientes ÷ clientes, como el «Ticket Pro.» de la Liquidación de Cajero. Los descuentos se miden sobre el precio de carta.</p></section>
      <section><h2>Costo real</h2><p>Inventario inicial + compras netas de notas de crédito − inventario final, con los cierres del mes operativo, sobre la venta de Costos: Alimentos, Bebidas, Vinos y Envases, con Eventos y sin Venta interna.</p></section>
      <section><h2>Costo del Sistema y sin explicar</h2><p>Costo histórico de los pedidos según el POS, incluidos combos, con notas de crédito restadas. Sin explicar = consumo carta − costo del Sistema − bajas: revisar fechas, alcance y valorización antes de atribuirlo a una causa.</p><p><strong>En Inforest:</strong> Paloteo de Producción → Comparativo → Ventas en el rango.</p></section>
    </div></details>`;
}

function render(raiz, d) {
  const a = d.actual, b = d.anterior, c = d.costo;
  // El aviso del mes en curso va en el subtítulo: un renglón propio sacaba
  // el pie del gráfico de la primera pantalla.
  const alcance = d.parcial
    ? `<span class="re-encurso">Mes en curso</span> · ventas del ${fecha(d.ini)} al ${fecha(d.fin)}, sin el día de hoy · el costo espera el cierre`
    : `Ventas al ${fecha(d.fin)} · día del turno, sin IGV${c?.cierre ? ` · Costos del cierre ${esc(c.cierre)}` : ''}`;
  raiz.innerHTML = `<header class="re-head"><div class="re-titulo"><h1>Resumen ejecutivo</h1><p class="muted">${alcance}</p></div><label class="re-select">Mes <select aria-label="Mes del resumen">${d.meses.map(m => `<option value="${esc(m.k)}" ${m.k === d.mes ? 'selected' : ''}>${esc(m.nombre)}</option>`).join('')}</select></label></header>
    ${d.demo ? '<div class="re-note warning">Modo demo · datos de ejemplo, sin conexión a los datos del restaurante.</div>' : ''}
    ${!a ? '<div class="re-note warning">No se pudo leer la venta del período. Reintentá en unos segundos.</div>' : ''}
    <div class="re-kpis">${kpis(d)}</div>
    <div class="re-grid"><section class="re-panel"><div class="re-panel-head"><h2>Venta neta del mes</h2><div class="re-legend"><span><i class="re-swatch"></i>${esc(d.rotulo)}</span>${b ? `<span><i class="re-swatch prior"></i>${esc(d.anterior_rotulo)}${d.parcial ? ' · mismo tramo' : ''}</span>` : '<span>Sin año pasado comparable</span>'}</div><div class="re-toggle" aria-label="Tipo de evolución"><button type="button" data-modo="acumulado" aria-pressed="${raiz.__modo !== 'diario'}">Acumulado</button><button type="button" data-modo="diario" aria-pressed="${raiz.__modo === 'diario'}">Diario</button></div>${abrir(d.links.ventas, 'Ventas')}</div><div class="re-chart" role="img" aria-label="Evolución de la venta neta en soles, período actual y año pasado"></div></section>
    <section class="re-panel"><div class="re-panel-head"><h2>Para revisar</h2></div><div class="re-signals">${alertas(d)}</div></section></div>
    <div class="re-lower"><section class="re-panel"><div class="re-panel-head"><h2>Costo por familia</h2>${abrir(d.links.costos, 'Costos')}</div>${familias(d)}</section><section class="re-panel"><div class="re-panel-head"><h2>Del consumo real al costo del Sistema</h2>${abrir(d.links.costos, 'Ver detalle')}</div>${conciliacion(d)}</section></div>
    ${metodo(raiz)}
    <footer class="re-foot"><span>Período: ${fecha(d.ini)} – ${fecha(d.fin)}${c?.cierre ? ` · Cierre registrado: ${esc(c.cierre)}` : ''}</span><span>Los reportes se abren en otra pestaña ↗</span></footer>`;
}

function dibujarGrafico(raiz) {
  const caja = raiz.querySelector('.re-chart'), d = raiz.__datos;
  if (!caja || !d.actual) { if (caja) caja.innerHTML = '<p class="muted">Sin datos disponibles.</p>'; return; }
  const W = Math.max(230, caja.getBoundingClientRect().width), H = caja.getBoundingClientRect().height;
  const dias = Number(d.fin.slice(8, 10)), acumulado = raiz.__modo !== 'diario';
  const serie = datos => {
    const mapa = new Map((datos?.dias || []).map(x => [Number(x.dia.slice(8, 10)), x.venta]));
    let total = 0;
    return Array.from({length: dias}, (_, i) => { const v = mapa.get(i + 1) || 0; total += v; return acumulado ? total : v; });
  };
  const actual = serie(d.actual), anterior = d.anterior ? serie(d.anterior) : [];
  const valores = [...actual, ...anterior, 0], min = Math.min(...valores), max = Math.max(...valores);
  const rango = Math.max(1, max - min), inferior = min < 0 ? min - rango * .08 : 0, superior = max + rango * .15;
  const L = 52, R = 14, T = 10, B = 22;
  const x = i => L + (W - L - R) * i / Math.max(1, dias - 1);
  const y = v => H - B - (v - inferior) / (superior - inferior) * (H - T - B);
  const path = s => s.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const compacto = v => Math.abs(v) >= 1000 ? `${num(v / 1000, Math.abs(v) < 10000 ? 1 : 0)} mil` : num(v);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img"><title>Venta neta ${acumulado ? 'acumulada' : 'diaria'} en soles</title>`;
  for (let i = 0; i < 4; i++) {
    const v = inferior + (superior - inferior) * i / 3;
    svg += `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${esc(compacto(v))}</text>`;
  }
  const ticks = [...new Set([1, Math.ceil(dias / 2), dias])];
  for (const t of ticks) svg += `<text x="${x(t - 1)}" y="${H - 6}" text-anchor="${t === 1 ? 'start' : t === dias ? 'end' : 'middle'}">${t === dias ? `día ${t}` : t}</text>`;
  if (anterior.length) svg += `<path class="prior-line" d="${path(anterior)}"/>`;
  svg += `<path class="line" d="${path(actual)}"/>`;
  if (dias === 1) svg += `<circle class="point" cx="${x(0)}" cy="${y(actual[0])}" r="4"/>`;
  const z = dias - 1;
  // El rótulo va del lado de la línea que deja libre el año pasado.
  const abajo = anterior.length && anterior[z] > actual[z];
  const yr = abajo ? Math.min(H - B - 4, y(actual[z]) + 18) : Math.max(14, y(actual[z]) - 10);
  svg += `<text class="endpoint" x="${x(z)}" y="${yr}" text-anchor="end">${esc(soles(actual[z]))}</text>`;
  for (let i = 0; i < dias; i++) {
    const ancho = Math.max(1, (W - L - R) / Math.max(1, dias - 1));
    svg += `<rect class="hit" x="${Math.max(L, x(i) - ancho / 2)}" y="${T}" width="${Math.min(ancho, W - R - Math.max(L, x(i) - ancho / 2))}" height="${H - T - B}"><title>Día ${i + 1}: ${esc(soles(actual[i]))}${anterior.length ? ` · Año pasado: ${esc(soles(anterior[i]))}` : ''}</title></rect>`;
  }
  caja.innerHTML = svg + '</svg>';
}

export default function(component) {
  const {parentElement, data, setTriggerValue} = component;
  let raiz = parentElement.querySelector('.re');
  if (!raiz) {
    raiz = document.createElement('div'); raiz.className = 're'; parentElement.appendChild(raiz);
    raiz.__modo = 'acumulado';
  }
  raiz.__datos = data;
  render(raiz, data);
  raiz.querySelector('.re-method').addEventListener('toggle', e => {
    raiz.__contextoAbierto = e.target.open;
  });
  raiz.querySelector('select').addEventListener('change', e => {
    e.target.disabled = true;
    setTriggerValue('mes', e.target.value);
  });
  raiz.querySelectorAll('[data-modo]').forEach(b => b.addEventListener('click', () => {
    raiz.__modo = b.dataset.modo;
    raiz.querySelectorAll('[data-modo]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    dibujarGrafico(raiz);
  }));
  const observer = new ResizeObserver(() => dibujarGrafico(raiz));
  observer.observe(raiz.querySelector('.re-chart'));
  dibujarGrafico(raiz);
  return () => observer.disconnect();
}
