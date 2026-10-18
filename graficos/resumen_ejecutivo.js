// Ventas y costo mensual. Sólo el cambio de mes solicita datos a Python.
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const valido = v => v != null && Number.isFinite(v);
const num = (v, dec = 0) => valido(v) ? v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec}) : '—';
const soles = (v, dec = 0) => valido(v) ? `S/ ${num(v, dec)}` : '—';
const pct = v => valido(v) ? `${num(v * 100, 1)}%` : '—';
const pp = v => valido(v) ? `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 1)} pp` : '—';
const variacion = (a, b) => valido(a) && valido(b) && b > 0 ? (a - b) / b : null;
const fecha = s => s ? s.split('-').reverse().join('/') : '';
const abrir = (url, texto) => `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(texto)}, abre en otra pestaña">${esc(texto)} ↗</a>`;

function delta(v, base, inverso = false, puntos = false) {
  if (!valido(v)) return `<span>Sin base comparable</span>`;
  const clase = v === 0 ? '' : ((inverso ? v < 0 : v > 0) ? 'good' : 'bad');
  const texto = puntos ? pp(v) : `${v >= 0 ? '+' : '−'}${pct(Math.abs(v))}`;
  return `<span class="re-delta ${clase}">${esc(texto)}</span> ${esc(base)}`;
}

function kpi(label, value, context, tip) {
  return `<section class="re-kpi" aria-label="${esc(label)}"><div class="re-label" title="${esc(tip || label)}">${esc(label)}</div><div class="re-value">${esc(value)}</div><div class="re-context">${context}</div></section>`;
}

function senal(titulo, detalle, valor, clase, link, texto) {
  return `<div class="re-signal"><span class="re-symbol ${clase}" aria-hidden="true">${clase === 'good' ? '↗' : '!'}</span><div><strong>${esc(titulo)}</strong><p>${esc(detalle)}</p>${abrir(link, texto)}</div><span class="amount ${clase}">${esc(valor)}</span></div>`;
}

function alertas(d) {
  const a = d.actual, c = d.costo, out = [];
  if (c && valido(d.cambio_costo)) out.push(senal(
    d.cambio_costo > 0 ? 'El costo operativo subió frente al mes anterior' : 'Variación del costo operativo',
    'Comparación entre meses completos y con la misma base de venta de Costos.', pp(d.cambio_costo),
    d.cambio_costo > 0 ? 'bad' : 'good', d.links.costos, 'Revisar costos'));
  if (c && Math.abs(c.diferencia) > 0.01) out.push(senal(
    c.diferencia > 0 ? 'El consumo carta supera el costo ajustado del POS' : 'El consumo carta es menor que el costo ajustado del POS',
    'La diferencia incluye bajas registradas y el faltante no registrado.', soles(c.diferencia),
    c.diferencia > 0 ? 'warn' : '', d.links.costos, 'Ver diferencia'));
  if (a && a.sin_costo > 0) out.push(senal('Ventas sin costo registrado en el POS',
    'El costo de estos platos queda en cero en la foto del POS y reduce su porcentaje de costo.',
    soles(a.sin_costo), 'warn', d.links.platos, 'Revisar platos'));
  if (a && d.anterior) {
    const v = variacion(a.venta, d.anterior.venta);
    if (valido(v)) out.push(senal(v >= 0 ? 'La venta crece frente al año pasado' : 'La venta disminuye frente al año pasado',
      `Mismas fechas del calendario: ${fecha(d.ini)} – ${fecha(d.fin)}.`, `${v >= 0 ? '+' : '−'}${pct(Math.abs(v))}`,
      v >= 0 ? 'good' : 'bad', d.links.ventas, 'Abrir ventas'));
  }
  return out.slice(0, 3).join('') || '<p class="muted">No hay una base suficiente para generar señales comparables en este período.</p>';
}

function bloqueCosto(d) {
  const c = d.costo;
  if (!c) return `<div class="re-empty">${esc(d.error_costos || (d.parcial ? 'Mes en curso: el consumo mensual estará disponible cuando existan sus cierres.' : 'Sin dos cierres consecutivos para calcular el consumo de este mes.'))}</div>`;
  const max = Math.max(1, ...c.familias.map(f => Math.abs(f.operativo)));
  return `<div class="re-total"><strong>${pct(c.porcentaje)}</strong><span class="re-context">${delta(d.cambio_costo, 'vs. mes anterior', true, true)}</span></div>
    <p class="muted">Consumo operativo ${soles(c.operativo)}</p>
    <div class="re-familias">${c.familias.map(f => `<div class="re-fila"><span>${esc(f.familia)}</span><div class="re-track"><div class="re-bar ${f.familia.toLowerCase()}" style="width:${Math.min(100, Math.abs(f.operativo) / max * 100)}%"></div></div><div class="num"><b>${pct(f.porcentaje)}</b><div class="re-small">${soles(f.operativo)}</div></div></div>`).join('')}</div>
    <p class="re-small">Base de venta de Costos: ${soles(c.venta_base)}. Alimentos, Bebidas, Vinos y Envases; incluye Eventos, sin Venta interna. Envases no tiene venta propia.</p>`;
}

function conciliacion(d) {
  const c = d.costo;
  if (!c) return '<div class="re-empty">La conciliación requiere el consumo mensual del período.</div>';
  const fila = (label, v, cl = '') => `<div class="re-ledger-row ${cl}"><span>${esc(label)}</span><b>${soles(v)}</b></div>`;
  return `<div class="re-ledger">${fila('Consumo operativo', c.operativo)}${fila('− Consumos no vendidos', c.no_vendido)}${fila('= Consumo carta', c.carta, 'total')}${fila('Costo ajustado del POS', c.pos)}${fila('Diferencia', c.diferencia, 'total')}${fila('Bajas registradas', c.bajas)}${fila('Faltante no registrado', c.faltante)}</div>
    <p class="re-small">Los consumos no vendidos incluyen cortesías, descuentos netos de devolución del banco y salidas distintas de bajas. La diferencia compara consumo carta con costo del POS ajustado por descuentos.</p>`;
}

function render(raiz, d) {
  const a = d.actual, b = d.anterior, c = d.costo;
  const ap = b ? `vs. ${d.anterior_rotulo}${d.parcial ? ' · mismo tramo' : ''}` : '';
  raiz.innerHTML = `<header class="re-head"><div><h1>Resumen ejecutivo</h1><p class="muted">Ventas, consumo y costo del restaurante.</p></div><label class="re-select">Mes <select aria-label="Mes del resumen">${d.meses.map(m => `<option value="${esc(m.k)}" ${m.k === d.mes ? 'selected' : ''}>${esc(m.nombre)}</option>`).join('')}</select></label></header>
    ${d.demo ? '<div class="re-note warning">Modo demo · datos de ejemplo, sin conexión a los datos del restaurante.</div>' : ''}
    ${d.parcial ? `<div class="re-note">Mes en curso · ventas del ${fecha(d.ini)} al ${fecha(d.fin)}. Se excluye el día de hoy para comparar días completos.</div>` : ''}
    ${!a ? '<div class="re-note warning">No se pudo leer la venta del período. Reintentá en unos segundos.</div>' : ''}
    <div class="re-kpis">
      ${kpi('Venta neta', soles(a?.venta), delta(variacion(a?.venta, b?.venta), ap), 'Todos los grupos de Ventas, sin IGV ni recargo; notas de crédito restadas.')}
      ${kpi('Pedidos netos', num(a?.pedidos), delta(variacion(a?.pedidos, b?.pedidos), ap), 'Un pedido una vez; las notas de crédito restan y el canje no duplica pedidos.')}
      ${kpi('Venta neta por pedido', soles(a?.promedio, 2), delta(variacion(a?.promedio, b?.promedio), ap), 'Venta neta dividida entre pedidos netos; no es el ticket por adulto del POS.')}
      ${kpi('Costo operativo / venta de Costos', pct(c?.porcentaje), c ? delta(d.cambio_costo, 'vs. mes anterior', true, true) : (d.parcial ? 'Disponible al cerrar el mes' : 'Sin cierre comparable'), 'Usa la base de venta de Costos, que se detalla en el panel de consumo.')}
    </div>
    <div class="re-grid"><section class="re-panel"><div class="re-panel-head"><div><h2>Venta neta durante el mes</h2><p class="muted">${esc(d.rotulo)} · ${d.parcial ? 'mismo tramo del año pasado' : 'mismo mes del año pasado'}</p></div>${abrir(d.links.ventas, 'Abrir ventas')}</div><div class="re-head"><div class="re-legend"><span><i class="re-swatch"></i>${esc(d.rotulo)}</span>${b ? `<span><i class="re-swatch prior"></i>${esc(d.anterior_rotulo)}</span>` : '<span>Sin año pasado comparable</span>'}</div><div class="re-toggle" aria-label="Tipo de evolución"><button type="button" data-modo="acumulado" aria-pressed="${raiz.__modo !== 'diario'}">Acumulado</button><button type="button" data-modo="diario" aria-pressed="${raiz.__modo === 'diario'}">Diario</button></div></div><div class="re-chart" role="img" aria-label="Evolución de venta neta en soles, período actual y año pasado"></div><p class="re-small">Venta total de todos los grupos · día del turno de caja · sin IGV ni recargo.</p></section>
    <section class="re-panel"><div class="re-panel-head"><div><h2>Control de costo operativo</h2><p class="muted">Consumo del mes operativo cerrado</p></div>${abrir(d.links.costos, 'Abrir costos')}</div>${bloqueCosto(d)}</section></div>
    <div class="re-lower"><section class="re-panel"><div class="re-panel-head"><h2>Señales para revisar</h2></div><div>${alertas(d)}</div></section><section class="re-panel"><div class="re-panel-head"><h2>Consumo y diferencia de costo</h2>${abrir(d.links.costos, 'Ver detalle')}</div>${conciliacion(d)}</section></div>
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
  const L = 66, R = 18, T = 24, B = 42;
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
  for (const t of ticks) svg += `<text x="${x(t - 1)}" y="${H - 24}" text-anchor="${t === 1 ? 'start' : t === dias ? 'end' : 'middle'}">${t}</text>`;
  svg += `<text x="0" y="12">Soles</text><text x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">Día del mes</text>`;
  if (anterior.length) svg += `<path class="prior-line" d="${path(anterior)}"/>`;
  svg += `<path class="line" d="${path(actual)}"/>`;
  if (dias === 1) svg += `<circle class="point" cx="${x(0)}" cy="${y(actual[0])}" r="4"/>`;
  const z = dias - 1;
  svg += `<text class="endpoint" x="${x(z)}" y="${Math.max(14, y(actual[z]) - 12)}" text-anchor="end">${esc(soles(actual[z]))}</text>`;
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
