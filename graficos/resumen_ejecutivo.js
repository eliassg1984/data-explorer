// Portada de Inicio (regla #745). Arriba, una frase que dice cómo fue el mes
// y cinco indicadores con sus doce meses; tocar uno cambia el gráfico grande.
// Al costado, «Para revisar»: las señales del mes y las de Pendientes en una
// lista, el detalle al tocar. Debajo, el costo por familia y el puente de lo
// sin explicar. A Python vuelven sólo el mes, el salto a un reporte y
// «Calcular»; lo demás lo resuelve el navegador.
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const valido = v => v != null && Number.isFinite(v);
const num = (v, dec = 0) => valido(v) ? v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec}) : '—';
const soles = (v, dec = 0) => valido(v) ? `${v < 0 ? '−' : ''}S/ ${num(Math.abs(v), dec)}` : '—';
const pct = (v, dec = 1) => valido(v) ? `${num(v * 100, dec)}%` : '—';
const signo = v => v >= 0 ? '+' : '−';
const pp = v => valido(v) ? `${signo(v)}${num(Math.abs(v) * 100, 1)} pp` : '—';
const varp = v => valido(v) ? `${signo(v)}${num(Math.abs(v) * 100, 1)}%` : '—';
const variacion = (a, b) => valido(a) && valido(b) && b > 0 ? a / b - 1 : null;
const mil = v => Math.abs(v) >= 1000 ? `${num(v / 1000, Math.abs(v) < 10000 ? 1 : 0)} mil` : num(v);
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const MES_L = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'setiembre', 'octubre', 'noviembre', 'diciembre'];
const DIA = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const rot = k => { const [y, m] = k.split('-'); return `${MES[m - 1]} ${y.slice(2)}`; };
const rotL = k => { const [y, m] = k.split('-'); return `${MES_L[m - 1].replace(/^./, c => c.toUpperCase())} ${y}`; };
const fechaIso = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const masDias = (f, n) => new Date(f.getFullYear(), f.getMonth(), f.getDate() + n);
const diaTxt = f => `${DIA[f.getDay()]} ${f.getDate()} ${MES[f.getMonth()]}`;
const fechaCorta = s => s ? s.split('-').reverse().join('/') : '';
const NIVEL = {rojo: 'bad', ambar: 'warn', verde: 'ok'};

// Un cambio se pinta por lo que SIGNIFICA: en costo y descuentos, subir es malo.
function cambio(v, base, {inverso = false, puntos = false} = {}) {
  if (!valido(v)) return '<span class="tenue">Sin base comparable</span>';
  const clase = Math.abs(v) < 1e-9 ? '' : ((inverso ? v < 0 : v > 0) ? 'good' : 'bad');
  return `<span class="re-delta ${clase}">${esc(puntos ? pp(v) : varp(v))}</span> ${esc(base)}`;
}

// «el más alto desde diciembre»: cuántos meses seguidos de antes quedan por
// debajo (o por encima) del último. Los meses en curso no cuentan.
function racha(hist, valor) {
  const vals = hist.map(h => (h.parcial && h !== hist[hist.length - 1]) ? null : valor(h));
  const ult = vals[vals.length - 1];
  if (!valido(ult)) return null;
  for (const [mayor, txt] of [[true, 'el más alto'], [false, 'el más bajo']]) {
    let k = 0, corte = null;
    for (let i = vals.length - 2; i >= 0; i--) {
      if (!valido(vals[i])) continue;
      if (mayor ? vals[i] < ult : vals[i] > ult) k++; else { corte = hist[i].k; break; }
    }
    if (k >= 2) return corte ? `${txt} desde ${MES_L[Number(corte.slice(5)) - 1]}${corte.slice(0, 4) !== hist[hist.length - 1].k.slice(0, 4) ? ` ${corte.slice(0, 4)}` : ''}` : `${txt} de los últimos ${k + 1} meses`;
  }
  return null;
}

function indicadores(d) {
  const a = d.actual || {}, b = d.anterior, c = d.costo, H = d.hist, h = H[H.length - 1];
  const ap = b ? `vs ${d.anterior_corto}` : '';
  const ppto = valido(h.ppto) && h.ppto > 0 ? h.venta / h.ppto : null;
  const clsPpto = !valido(ppto) ? '' : ppto >= 1 ? 'good' : ppto < 0.95 ? 'bad' : '';
  const hab = d.habitual || {};
  const lista = [
    {id: 'venta', lab: 'Venta neta', val: soles(a.venta),
     meter: valido(ppto) ? Math.min(1, ppto) : null, clsMeter: clsPpto,
     l1: valido(ppto) ? `<span class="re-delta ${clsPpto}">${esc(pct(ppto, 0))}</span> del presupuesto${d.parcial ? ' a la fecha' : ''}`
                      : cambio(variacion(a.venta, b?.venta), ap),
     l2: valido(ppto) ? cambio(variacion(a.venta, b?.venta), ap) : `${num(a.pedidos)} pedidos`,
     serie: H.map(x => x.venta), serie2: H.map(x => x.ppto), aditiva: true,
     tip: 'Todos los grupos de Ventas, por día del turno; pagados y por cobrar, menos notas de crédito; sin IGV ni recargo. El presupuesto es el neto que se carga en Costos.'},
    {id: 'clientes', lab: 'Clientes', val: num(a.clientes),
     l1: cambio(variacion(a.clientes, b?.clientes), ap),
     l2: (!d.parcial && racha(H, x => x.clientes)) || `${num(a.pedidos)} pedidos`,
     serie: H.map(x => x.clientes), aditiva: true,
     tip: 'Adultos, una vez por pedido; una nota de crédito resta.'},
    {id: 'ticket', lab: 'Ticket por cliente', val: soles(a.ticket, 2),
     l1: cambio(variacion(a.ticket, b?.ticket), ap),
     l2: valido(hab.ticket) ? `habitual ${soles(hab.ticket, 2)}` : '',
     serie: H.map(x => x.ticket),
     tip: 'Venta de los canales que registran clientes ÷ clientes, como el «Ticket Pro.» de la Liquidación de Cajero. Lo habitual es la mediana de los seis meses anteriores.'},
    {id: 'desc', lab: 'Descuentos', val: pct(a.pct_descuento),
     l1: b && valido(b.pct_descuento) ? cambio(a.pct_descuento - b.pct_descuento, ap, {inverso: true, puntos: true}) : '<span class="tenue">Sin base comparable</span>',
     l2: `${soles(a.descuentos)} sobre la carta`,
     serie: H.map(x => x.pct_descuento),
     tip: 'Lo que se dejó de cobrar sobre el precio de carta, con impuestos, como «Descuentos» de Ventas › Resumen. El cambio es en puntos.'},
    {id: 'costo', lab: 'Costo de ventas', val: c ? pct(c.porcentaje) : '—',
     l1: c ? (d.costo_ap ? cambio(c.porcentaje - d.costo_ap.porcentaje, ap, {inverso: true, puntos: true})
                         : d.previo ? cambio(c.porcentaje - d.previo.porcentaje, `vs ${d.previo_corto}`, {inverso: true, puntos: true}) : '')
           : `<span class="tenue">${d.parcial ? 'Al cerrar el mes' : 'Sin cierre comparable'}</span>`,
     l2: c ? `Sistema ${pct(c.porcentaje_pos)} · sin explicar ${pct(c.porcentaje_faltante)}`
           : (d.previo ? `${d.previo_corto}: ${pct(d.previo.porcentaje)}` : ''),
     serie: H.map(x => x.costo?.real ?? null), serie2: H.map(x => x.costo?.pos ?? null),
     tip: 'Real: inventario inicial + compras − final, sobre la venta de Costos (Alimentos, Bebidas, Vinos y Envases; con Eventos; lo que va a Mayta, como salida y no como venta). Sistema: el costo de las recetas del POS sobre la misma venta. La distancia la explica el puente de abajo.'},
  ];
  return lista;
}

function htmlIndicadores(raiz, d) {
  raiz.__kpis = indicadores(d);
  return raiz.__kpis.map(k => `
    <button type="button" class="re-kpi" data-kpi="${k.id}" aria-pressed="${k.id === raiz.__kpi}" title="${esc(k.tip)}">
      <span class="re-label">${esc(k.lab)}</span>
      <span class="re-value">${esc(k.val)}</span>
      <span class="re-spark" data-spark="${k.id}" aria-hidden="true"></span>
      ${k.meter != null ? `<span class="re-meter" aria-hidden="true"><i class="${k.clsMeter}" style="width:${(k.meter * 100).toFixed(1)}%"></i></span>` : ''}
      <span class="re-l1">${k.l1}</span><span class="re-l2">${k.l2 || '&nbsp;'}</span>
    </button>`).join('');
}

function dibujarSparks(raiz) {
  const H = raiz.__datos.hist;
  raiz.querySelectorAll('[data-spark]').forEach(caja => {
    const k = (raiz.__kpis || []).find(x => x.id === caja.dataset.spark);
    const W = caja.clientWidth, Hh = caja.clientHeight;
    if (!k || !W || !Hh) return;
    const todos = [...k.serie, ...(k.serie2 || [])].filter(valido);
    if (todos.length < 2) { caja.innerHTML = ''; return; }
    const lo = Math.min(...todos), hi = Math.max(...todos), r = hi - lo || 1, n = k.serie.length - 1;
    const x = i => 2 + (W - 6) * i / Math.max(1, n);
    const y = v => Hh - 3 - (v - lo) / r * (Hh - 6);
    // El último mes en curso, si es una suma, se ve partido y hueco.
    const corta = k.aditiva && H[n].parcial;
    const linea = (s, hasta) => { let p = '', pluma = false; s.forEach((v, i) => { if (i > hasta || !valido(v)) { pluma = false; return; } p += `${pluma ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pluma = true; }); return p; };
    const fin = corta ? n - 1 : n;
    let svg = `<svg viewBox="0 0 ${W} ${Hh}">`;
    if (k.serie2) svg += `<path class="sp2 ${k.id === 'venta' ? 'ppto' : ''}" d="${linea(k.serie2, n)}"/>`;
    svg += `<path class="sp" d="${linea(k.serie, fin)}"/>`;
    if (corta && valido(k.serie[n]) && valido(k.serie[n - 1])) svg += `<path class="sp corta" d="M${x(n - 1)},${y(k.serie[n - 1])}L${x(n)},${y(k.serie[n])}"/>`;
    if (valido(k.serie[n])) svg += `<circle class="${corta ? 'hueco' : ''}" cx="${x(n)}" cy="${y(k.serie[n])}" r="3"/>`;
    caja.innerHTML = svg + '</svg>';
  });
}

// ── El gráfico grande ───────────────────────────────────────────────────
function pasos(lo, hi, n = 4) {
  const span = (hi - lo) || Math.abs(hi) || 1, bruto = span / n, mag = 10 ** Math.floor(Math.log10(bruto)), e = bruto / mag;
  const paso = (e >= 7.5 ? 10 : e >= 3.5 ? 5 : e >= 1.5 ? 2 : 1) * mag;
  const a = Math.floor(lo / paso) * paso, b = Math.ceil(hi / paso) * paso, t = [];
  for (let v = a; v <= b + paso / 1e6; v += paso) t.push(+v.toFixed(8));
  return t;
}
const acum = s => { let t = 0; return s.map(v => (t += (v || 0))); };

function spec(raiz) {
  const d = raiz.__datos, H = d.hist, k = raiz.__kpi, dia = d.diario || {};
  if (k === 'venta' && raiz.__escala === 'mes' && dia.actual) {
    const ac = raiz.__modo !== 'diario', f = ac ? acum : s => s, n = dia.actual.length;
    const a = f(dia.actual), ap = dia.ap ? f(dia.ap) : null, p = dia.ppto ? f(dia.ppto) : null;
    const ini = fechaIso(dia.ini), apIni = fechaIso(dia.ap_ini);
    const nombreMes = MES_L[ini.getMonth()];
    const series = [];
    if (p) series.push({clase: 'l-pp', vals: p, fin: ac ? `Ppto ${mil(p[n - 1])}` : null, finClase: 'pp'});
    if (ap) series.push({clase: 'l-ap', vals: ap, fin: ac ? `${apIni.getFullYear()}: ${mil(ap[n - 1])}` : null, finClase: 'ap'});
    series.push({clase: 'l-act', vals: a, area: true, fin: ac ? `S/ ${mil(a[n - 1])}` : null, pto: n === 1});
    const ticks = n <= 7 ? [...Array(n).keys()] : [0, 6, 13, 20, 27, n - 1].filter((t, i, s) => t < n && s.indexOf(t) === i);
    return {
      titulo: ac ? `Venta neta acumulada de ${nombreMes}` : `Venta neta por día de ${nombreMes}`,
      n, tipo: 'linea', cero: true, findes: masDias.bind(null, ini), fmtY: mil,
      etiquetaX: i => String(masDias(ini, i).getDate()), ticksX: raiz.querySelector('.re-chart')?.clientWidth < 460 ? ticks.filter(t => t !== 27) : ticks,
      series,
      leyenda: [['', rotL(d.mes)], ...(ap ? [['ap', 'Año pasado, mismo día de la semana']] : []), ...(p ? [['pp', 'Presupuesto']] : []), ['fin', 'Sáb y dom']],
      ficha: i => ({t: diaTxt(masDias(ini, i)) + (ac ? ' · acumulado' : ''), r: [
        ['Venta', soles(a[i])],
        ...(ap ? [[`Año pasado (${diaTxt(masDias(apIni, i))})`, `${soles(ap[i])}${valido(variacion(a[i], ap[i])) ? ` · ${varp(variacion(a[i], ap[i]))}` : ''}`]] : []),
        ...(p ? [['Presupuesto', `${soles(p[i])}${p[i] > 0 ? ` · ${pct(a[i] / p[i], 0)}` : ''}`]] : [])]}),
      pie: ac ? '' : 'El año pasado cae en el mismo día de la semana: un sábado se compara con un sábado.',
    };
  }
  const sel = H.length - 1, comun = {n: H.length, etiquetaX: i => rot(H[i].k), ticksX: H.map((_, i) => i), sel};
  const ap = (x, campo) => x.ap ? x.ap[campo] : null;
  const enCurso = i => H[i].parcial ? ' (en curso)' : '';
  if (k === 'venta') return {...comun, titulo: 'Venta neta, últimos 12 meses', tipo: 'barras', cero: true, fmtY: mil,
    parcial: H.map(x => x.parcial),
    series: [{barras: H.map(x => x.venta)}, {marcas: H.map(x => ap(x, 'venta')), clase: 'm-ap'}, {marcas: H.map(x => x.ppto), clase: 'm-pp'}],
    leyenda: [['bar', 'Venta'], ['ap', 'Año pasado'], ...(H.some(x => valido(x.ppto)) ? [['pp', 'Presupuesto']] : [])],
    ficha: i => ({t: rotL(H[i].k) + enCurso(i), r: [['Venta', soles(H[i].venta)],
      ...(valido(H[i].ppto) ? [['Presupuesto', `${soles(H[i].ppto)} · ${pct(H[i].venta / H[i].ppto, 0)}`]] : []),
      ['Año pasado', valido(ap(H[i], 'venta')) ? `${soles(ap(H[i], 'venta'))} · ${varp(variacion(H[i].venta, ap(H[i], 'venta')))}` : 'sin datos']]}),
    pie: H[H.length - 1].parcial ? 'El mes en curso se compara con sus mismos días.' : ''};
  if (k === 'clientes') return {...comun, titulo: 'Clientes por mes', tipo: 'barras', cero: true, fmtY: v => num(v),
    parcial: H.map(x => x.parcial),
    series: [{barras: H.map(x => x.clientes)}, {marcas: H.map(x => ap(x, 'clientes')), clase: 'm-ap'}],
    leyenda: [['bar', 'Clientes (adultos)'], ['ap', 'Año pasado']],
    ficha: i => ({t: rotL(H[i].k) + enCurso(i), r: [['Clientes', num(H[i].clientes)], ['Pedidos', num(H[i].pedidos)],
      ['Año pasado', valido(ap(H[i], 'clientes')) ? `${num(ap(H[i], 'clientes'))} · ${varp(variacion(H[i].clientes, ap(H[i], 'clientes')))}` : 'sin datos']]}),
    pie: ''};
  if (k === 'ticket') return {...comun, titulo: 'Ticket por cliente', tipo: 'linea', cero: false, fmtY: v => `S/ ${num(v)}`,
    series: [{clase: 'l-ap', vals: H.map(x => ap(x, 'ticket'))}, {clase: 'l-act', vals: H.map(x => x.ticket), pto: true}],
    leyenda: [['', 'Ticket'], ['ap', 'Año pasado']],
    ficha: i => ({t: rotL(H[i].k) + enCurso(i), r: [['Ticket', soles(H[i].ticket, 2)],
      ['Año pasado', valido(ap(H[i], 'ticket')) ? `${soles(ap(H[i], 'ticket'), 2)} · ${varp(variacion(H[i].ticket, ap(H[i], 'ticket')))}` : 'sin datos']]}),
    pie: ''};
  if (k === 'desc') return {...comun, titulo: 'Descuentos, % de la carta', tipo: 'linea', cero: false, fmtY: v => `${num(v * 100)}%`,
    series: [{clase: 'l-ap', vals: H.map(x => ap(x, 'pct_descuento'))}, {clase: 'l-act', vals: H.map(x => x.pct_descuento), pto: true}],
    leyenda: [['', 'Descuentos'], ['ap', 'Año pasado']],
    ficha: i => ({t: rotL(H[i].k) + enCurso(i), r: [['Sobre la carta', pct(H[i].pct_descuento)], ['En soles', soles(H[i].descuentos)],
      ['Año pasado', valido(ap(H[i], 'pct_descuento')) ? `${pct(ap(H[i], 'pct_descuento'))} · ${pp(H[i].pct_descuento - ap(H[i], 'pct_descuento'))}` : 'sin datos']]}),
    pie: ''};
  const real = H.map(x => x.costo?.real ?? null), pos = H.map(x => x.costo?.pos ?? null);
  return {...comun, titulo: 'Costo de ventas: real y del Sistema', tipo: 'linea', cero: false, fmtY: v => `${num(v * 100)}%`,
    series: [{clase: 'l-sis', vals: pos, pto: true, ptoClase: 'sis'}, {clase: 'l-act', vals: real, pto: true}],
    entre: [pos, real],
    leyenda: [['', 'Real (inventario)'], ['sis', 'Sistema (recetas del POS)']],
    ficha: i => ({t: rotL(H[i].k), r: H[i].costo ? [['Real', pct(H[i].costo.real)], ['Sistema', pct(H[i].costo.pos)],
      ['Sin explicar', `${soles(H[i].costo.faltante)} · ${pct(H[i].costo.faltante_pct)}`], ['Vendido sin costo', pct(H[i].sin_costo_pct)]]
      : [['Costo', H[i].parcial ? 'espera el cierre' : 'sin dos cierres']]}),
    pie: 'Entre las dos líneas: cortesías, salidas, bajas y lo sin explicar.'};
}

function dibujarGrafico(raiz) {
  const caja = raiz.querySelector('.re-chart'), sp = spec(raiz);
  raiz.querySelector('.re-chart-tit').textContent = sp.titulo;
  raiz.querySelector('.re-chart-pie').textContent = sp.pie || '';
  raiz.querySelector('.re-legend').innerHTML = sp.leyenda.map(([c, t]) => `<span><i class="re-sw ${c}"></i>${esc(t)}</span>`).join('');
  const W = caja.clientWidth, H = caja.clientHeight;
  if (!W || !H) return;
  const finales = sp.series.some(s => s.fin);
  const L = 52, R = finales ? 90 : 12, T = 10, B = 24, barras = sp.tipo === 'barras', n = sp.n;
  const vals = sp.series.flatMap(s => s.vals || s.barras || s.marcas || []).filter(valido);
  if (!vals.length) { caja.innerHTML = '<p class="tenue re-vacio">Sin datos para este indicador.</p>'; return; }
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (sp.cero) lo = Math.min(0, lo); else { const m = (hi - lo) * 0.15 || Math.abs(hi) * 0.1 || 1; lo -= m; hi += m; }
  const ticks = pasos(lo, hi); lo = ticks[0]; hi = ticks[ticks.length - 1];
  const ancho = (W - L - R) / (barras ? n : Math.max(1, n - 1));
  const x = i => barras ? L + ancho * (i + 0.5) : (n === 1 ? L + (W - L - R) / 2 : L + ancho * i);
  const y = v => H - B - (v - lo) / ((hi - lo) || 1) * (H - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(sp.titulo)}">`;
  if (sp.findes) for (let i = 0; i < n; i++) {
    const g = sp.findes(i).getDay();
    if (g === 6 || g === 0) svg += `<rect class="finde" x="${Math.max(L, x(i) - ancho / 2)}" y="${T}" width="${Math.min(ancho, W - R - Math.max(L, x(i) - ancho / 2))}" height="${H - T - B}"/>`;
  }
  for (const t of ticks) svg += `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L - 8}" y="${y(t) + 4}" text-anchor="end">${esc(sp.fmtY(t))}</text>`;
  for (const i of sp.ticksX) {
    const anc = barras ? 'middle' : i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle';
    svg += `<text class="${i === sp.sel ? 'x-sel' : ''}" x="${x(i)}" y="${H - 6}" text-anchor="${anc}">${esc(sp.etiquetaX(i))}</text>`;
  }
  const trazo = s => { let p = '', pluma = false; s.forEach((v, i) => { if (!valido(v)) { pluma = false; return; } p += `${pluma ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pluma = true; }); return p; };
  if (sp.entre) {
    const [a, b] = sp.entre, idx = a.map((v, i) => i).filter(i => valido(a[i]) && valido(b[i]));
    if (idx.length > 1) svg += `<path class="area" d="${idx.map((i, j) => `${j ? 'L' : 'M'}${x(i)},${y(a[i])}`).join('')}${idx.slice().reverse().map(i => `L${x(i)},${y(b[i])}`).join('')}Z"/>`;
  }
  const etiquetas = [];
  for (const s of sp.series) {
    if (s.barras) s.barras.forEach((v, i) => {
      if (!valido(v)) return;
      const y0 = y(Math.max(lo, 0)), y1 = y(v);
      svg += `<rect class="bar ${i === sp.sel ? 'sel' : ''} ${sp.parcial?.[i] ? 'parcial' : ''}" x="${x(i) - ancho * 0.32}" y="${Math.min(y0, y1)}" width="${ancho * 0.64}" height="${Math.abs(y0 - y1)}" rx="3"/>`;
    });
    if (s.marcas) s.marcas.forEach((v, i) => {
      if (valido(v)) svg += `<line class="${s.clase}" x1="${x(i) - ancho * 0.42}" x2="${x(i) + ancho * 0.42}" y1="${y(v)}" y2="${y(v)}"/>`;
    });
    if (s.vals) {
      if (s.area) svg += `<path class="area" d="${trazo(s.vals)} L${x(n - 1)},${y(lo)} L${x(0)},${y(lo)}Z"/>`;
      svg += `<path class="${s.clase}" d="${trazo(s.vals)}"/>`;
      if (s.pto) s.vals.forEach((v, i) => { if (valido(v)) svg += `<circle class="pto ${s.ptoClase || ''}" cx="${x(i)}" cy="${y(v)}" r="${i === sp.sel ? 4.5 : 3}"/>`; });
      if (s.fin && valido(s.vals[n - 1])) etiquetas.push({y: y(s.vals[n - 1]), t: s.fin, c: s.finClase || ''});
    }
  }
  // Los rótulos del final, en el margen derecho y sin pisarse.
  etiquetas.sort((a, b) => a.y - b.y);
  for (let i = 1; i < etiquetas.length; i++) etiquetas[i].y = Math.max(etiquetas[i].y, etiquetas[i - 1].y + 15);
  for (const e of etiquetas) svg += `<text class="fin-t ${e.c}" x="${W - R + 6}" y="${e.y + 4}">${esc(e.t)}</text>`;
  svg += `<line class="cruz" x1="0" x2="0" y1="${T}" y2="${H - B}" visibility="hidden"/>`;
  svg += `<rect class="toque" x="${L}" y="${T}" width="${Math.max(0, W - L - R)}" height="${H - T - B}"/>`;
  caja.innerHTML = svg + '</svg><div class="re-ficha" hidden></div>';
  const ficha = caja.querySelector('.re-ficha'), cruz = caja.querySelector('.cruz'), toque = caja.querySelector('.toque');
  const mover = ev => {
    const r = caja.getBoundingClientRect(), px = ev.clientX - r.left;
    let i = barras ? Math.floor((px - L) / ancho) : Math.round((px - L) / ancho);
    i = Math.max(0, Math.min(n - 1, i));
    cruz.setAttribute('x1', x(i)); cruz.setAttribute('x2', x(i)); cruz.setAttribute('visibility', 'visible');
    const f = sp.ficha(i);
    ficha.innerHTML = `<div class="t">${esc(f.t)}</div>` + f.r.map(([a, b]) => `<div class="r"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
    ficha.hidden = false;
    const fw = ficha.offsetWidth, izq = x(i) + 14 + fw > W ? x(i) - 14 - fw : x(i) + 14;
    ficha.style.left = `${Math.max(0, izq)}px`; ficha.style.top = `${T + 4}px`;
  };
  const salir = () => { ficha.hidden = true; cruz.setAttribute('visibility', 'hidden'); };
  toque.addEventListener('pointermove', mover);
  toque.addEventListener('pointerdown', mover);
  toque.addEventListener('pointerleave', salir);
}

// ── Para revisar ────────────────────────────────────────────────────────
function formato(v, forma) {
  return forma === 'soles' ? soles(v, 2) : forma === 'num' ? num(v) : pct(v);
}

function miniHist(serie, forma) {
  const vals = serie.map(([, v]) => v).filter(valido);
  if (vals.length < 3) return '';
  const max = Math.max(...vals.map(Math.abs)) || 1;
  return `<div class="re-mini" aria-hidden="true">${serie.map(([r, v], i) =>
    `<i class="${i === serie.length - 1 ? 'sel' : ''}" style="height:${valido(v) ? Math.max(6, Math.abs(v) / max * 100) : 0}%" title="${esc(r)}: ${esc(valido(v) ? formato(v, forma) : 'sin dato')}"></i>`).join('')}</div>
    <div class="re-mini-eje"><span>${esc(serie[0][0])}</span><span>${esc(serie[serie.length - 1][0])}</span></div>`;
}

function htmlLista(raiz, d) {
  const items = d.items || [], abierto = raiz.__abierto;
  const filas = items.map((it, i) => `
    <div class="re-item"><button type="button" class="re-item-btn" data-item="${i}" aria-expanded="${abierto === i}" aria-controls="re-det-${i}">
      <span class="re-dot ${NIVEL[it.nivel] || 'warn'}" aria-hidden="true"></span><span class="re-tt">${esc(it.t)}</span>
      <span class="re-chip ${NIVEL[it.nivel] || 'warn'}">${esc(it.chip)}</span><span class="re-caret" aria-hidden="true">›</span></button>
      <div class="re-det" id="re-det-${i}" ${abierto === i ? '' : 'hidden'}>
        ${(it.det || []).map(t => `<p>${esc(t)}</p>`).join('')}
        ${it.serie ? miniHist(it.serie, it.forma) : ''}
        ${it.ir && d.destinos?.[it.ir] ? `<button type="button" class="re-ir" data-ir="${esc(it.ir)}">Ver en ${esc(d.destinos[it.ir])} ›</button>` : ''}
      </div></div>`).join('');
  const verdes = d.al_dia || [];
  const alDia = verdes.length ? `
    <div class="re-item"><button type="button" class="re-item-btn" data-item="al_dia" aria-expanded="${abierto === 'al_dia'}" aria-controls="re-det-al">
      <span class="re-dot ok" aria-hidden="true"></span><span class="re-tt">Al día</span>
      <span class="re-chip ok">${verdes.length}</span><span class="re-caret" aria-hidden="true">›</span></button>
      <div class="re-det" id="re-det-al" ${abierto === 'al_dia' ? '' : 'hidden'}><ul>${verdes.map(t => `<li>${esc(t)}</li>`).join('')}</ul></div></div>` : '';
  const vacio = !items.length ? '<p class="tenue re-nada">Nada que revisar con los datos de este período.</p>' : '';
  const pie = `<div class="re-revisar-pie">
      ${d.sin_calcular ? `<span><b>${num(d.sin_calcular)} ${d.sin_calcular === 1 ? 'control' : 'controles'}</b> sin calcular</span>` : '<span>Todos los controles calculados</span>'}
      ${d.sin_calcular && d.calculable ? '<button type="button" class="re-calc">Calcular (≈40 s)</button>' : ''}
      <button type="button" class="re-link re-ver-pend">Ver Pendientes ↓</button></div>`;
  const n = items.length;
  return `<div class="re-panel-head"><h2>Para revisar</h2><span class="tenue">${n ? `${n} para mirar` : ''}${n && verdes.length ? ' · ' : ''}${verdes.length ? `${verdes.length} al día` : ''}</span></div>
    <div class="re-lista">${filas}${alDia}${vacio}</div>${pie}`;
}

// ── El costo del mes ────────────────────────────────────────────────────
function htmlCosto(d) {
  const c = d.costo;
  if (!c) return `<div class="re-empty">${esc(d.error_costos || (d.parcial ? 'Mes en curso: el costo por familia y el puente estarán cuando exista su cierre.' : 'Sin dos cierres consecutivos para calcular este mes.'))}</div>`;
  const fams = (c.familias || []).filter(f => valido(f.porcentaje) && f.venta_base > 0);
  const sinVenta = (c.familias || []).filter(f => !(f.venta_base > 0) && Math.abs(f.operativo) > 0.5);
  const tope = Math.max(0.6, Math.ceil(Math.max(...fams.flatMap(f => [f.porcentaje, f.pos / f.venta_base]), 0) * 5) / 5);
  const p = v => `${Math.min(100, Math.max(0, v / tope * 100)).toFixed(1)}%`;
  const marcas = [0, tope / 3, 2 * tope / 3, tope].map(v => `<span>${num(v * 100)}%</span>`).join('');
  const filas = fams.map(f => {
    const real = f.porcentaje, sis = f.pos / f.venta_base, dif = real - sis;
    const a = Math.min(real, sis), b = Math.max(real, sis);
    return `<div class="re-fam"><span>${esc(f.familia)}</span>
      <div class="re-eje" aria-hidden="true"><i class="re-une ${dif < 0 ? 'menos' : ''}" style="left:${p(a)};width:calc(${p(b)} - ${p(a)})"></i>
        <i class="re-p s" style="left:${p(sis)}"></i><i class="re-p r" style="left:${p(real)}"></i></div>
      <span class="num"><b>${pct(real)}</b> · ${pct(sis)} · <span class="${Math.abs(dif) >= 0.05 ? 'warn' : ''}">${pp(dif)}</span></span></div>`;
  }).join('');
  const nota = sinVenta.map(f => `${esc(f.familia)}: ${soles(f.operativo)} de consumo, sin venta propia.`).join(' ');
  const w = v => `${Math.max(0, v / c.operativo * 100).toFixed(2)}%`;
  const fila = (nom, desde, hasta, v, cl) => `<div class="re-pr ${cl}"><span class="nom">${esc(nom)}</span>
    <div class="pista" aria-hidden="true"><i style="left:${w(Math.min(desde, hasta))};width:${w(Math.abs(hasta - desde))}"></i></div><span class="v">${soles(v)}</span></div>`;
  const puente = c.operativo > 0 ? [
    fila('Consumo real (contado)', 0, c.operativo, c.operativo, 'tot'),
    fila('− Cortesías y salidas', c.carta, c.operativo, -c.no_vendido, 'resta'),
    fila('= Consumo carta', 0, c.carta, c.carta, ''),
    fila('− Costo del Sistema', c.diferencia, c.carta, -c.pos, 'resta'),
    fila('− Bajas registradas', c.faltante, c.diferencia, -c.bajas, 'resta'),
    fila(`= Sin explicar · ${pct(c.porcentaje_faltante)}`, 0, c.faltante, c.faltante, 'fin'),
  ].join('') : '<div class="re-empty">Sin consumo para armar el puente.</div>';
  return `<div>
      <div class="re-panel-head"><h2>Costo por familia</h2><button type="button" class="re-link" data-ir="costos">Costos ›</button></div>
      <p class="re-sub">Real (inventario) contra Sistema (recetas del POS), sobre la venta de cada familia</p>
      <div class="re-fam re-fam-eje"><span></span><div>${marcas}</div><span class="num">Real · Sistema · Δ</span></div>
      ${filas}
      <p class="re-small"><i class="re-p-ley r"></i>Real <i class="re-p-ley s"></i>Sistema · Venta de Costos ${soles(c.venta_base)}, con Eventos y sin Venta interna.${nota ? ` ${nota}` : ''}</p>
    </div>
    <div>
      <div class="re-panel-head"><h2>De dónde sale lo sin explicar</h2><button type="button" class="re-link" data-ir="costos">Ver la conciliación ›</button></div>
      <p class="re-sub">El consumo del mes, en soles, de lo contado a lo que el Sistema no explica</p>
      <div class="re-puente">${puente}</div>
    </div>`;
}

function metodo(raiz) {
  return `<details class="re-method" ${raiz.__contextoAbierto ? 'open' : ''}><summary>Qué se cuenta y cómo se calcula</summary><div class="re-method-body">
      <section><h2>Venta neta y presupuesto</h2><p>Comprobantes pagados y por cobrar, menos notas de crédito, de todos los grupos; sin IGV ni recargo. Cada ítem se suma una vez aunque tenga varios pagos. El período usa el día del turno de caja. El presupuesto es el neto por mes que se carga en Costos; un mes en curso se compara con el presupuesto de sus mismos días.</p><p><strong>En Inforest:</strong> Registro de Ventas, con los mismos comprobantes y criterio de fecha.</p></section>
      <section><h2>Año pasado y lo habitual</h2><p>Los totales del mes se comparan con las mismas fechas del calendario un año antes. El gráfico día por día, con el día de la semana: 364 días antes. Lo habitual es la mediana de los seis meses anteriores.</p></section>
      <section><h2>Clientes, ticket y descuentos</h2><p>Clientes son adultos, una vez por pedido. El ticket es la venta de los canales que registran clientes ÷ clientes, como el «Ticket Pro.» de la Liquidación de Cajero. Los descuentos se miden sobre el precio de carta.</p></section>
      <section><h2>Costo real, del Sistema y sin explicar</h2><p>Real: inventario inicial + compras netas de notas de crédito − inventario final, con los cierres del mes operativo, sobre la venta de Costos (Alimentos, Bebidas, Vinos y Envases, con Eventos y sin Venta interna). Sistema: el costo histórico de los pedidos según el POS. Sin explicar = consumo carta − costo del Sistema − bajas; se marca cuando pasa el doble de lo habitual, como en Costos y en Pendientes.</p><p><strong>En Inforest:</strong> Paloteo de Producción → Comparativo → Ventas en el rango.</p></section>
    </div></details>`;
}

function render(raiz, d) {
  const sinVenta = !d.actual;
  const i = d.meses.findIndex(m => m.k === d.mes);
  const alcance = d.parcial
    ? `<span class="re-encurso">Mes en curso</span> · ventas del ${fechaCorta(d.ini)} al ${fechaCorta(d.fin)}, sin el día de hoy · sin IGV, por día del turno`
    : `Ventas sin IGV, por día del turno${d.costo?.cierre ? ` · costo con el cierre del ${esc(d.costo.cierre)}` : ''} · comparado con ${esc(d.anterior_corto)}`;
  const titular = (d.titular || []).map(([t, c]) => c ? `<strong class="${c === 'b' ? '' : c}">${esc(t)}</strong>` : esc(t)).join('');
  raiz.innerHTML = `<header class="re-head">
      <div class="re-mesnav">
        <button type="button" class="re-flecha" data-mes="${esc(d.meses[i + 1]?.k || '')}" ${d.meses[i + 1] ? '' : 'disabled'} aria-label="Mes anterior">‹</button>
        <label class="re-mes"><span class="re-oculto">Mes del resumen</span><select aria-label="Mes del resumen">${d.meses.map(m => `<option value="${esc(m.k)}" ${m.k === d.mes ? 'selected' : ''}>${esc(m.nombre)}</option>`).join('')}</select></label>
        <button type="button" class="re-flecha" data-mes="${esc(d.meses[i - 1]?.k || '')}" ${i > 0 ? '' : 'disabled'} aria-label="Mes siguiente">›</button>
      </div>
      <p class="re-alcance">${alcance}</p>
    </header>
    ${d.demo ? '<div class="re-note warning">Modo demo · datos de ejemplo, sin conexión a los datos del restaurante.</div>' : ''}
    ${sinVenta ? '<div class="re-note warning">No se pudo leer la venta del período. Reintentá en unos segundos.</div>' : ''}
    ${titular ? `<p class="re-titular">${titular}</p>` : ''}
    <div class="re-kpis" role="group" aria-label="Indicadores del mes: elegir uno cambia el gráfico">${htmlIndicadores(raiz, d)}</div>
    <div class="re-grid">
      <section class="re-panel re-graf" aria-label="Gráfico del indicador elegido">
        <div class="re-panel-head"><h2 class="re-chart-tit"></h2>
          <div class="re-seg" role="group" aria-label="Período del gráfico">
            <button type="button" data-escala="mes" aria-pressed="${raiz.__escala === 'mes'}">${esc(MES_L[Number(d.mes.slice(5)) - 1].replace(/^./, c => c.toUpperCase()))}</button>
            <button type="button" data-escala="anio" aria-pressed="${raiz.__escala === 'anio'}">12 meses</button>
          </div>
          <div class="re-seg re-seg-modo" role="group" aria-label="Forma">
            <button type="button" data-modo="acumulado" aria-pressed="${raiz.__modo !== 'diario'}">Acumulado</button>
            <button type="button" data-modo="diario" aria-pressed="${raiz.__modo === 'diario'}">Diario</button>
          </div>
        </div>
        <div class="re-legend"></div>
        <div class="re-chart"></div>
        <p class="re-chart-pie"></p>
      </section>
      <section class="re-panel re-revisar" aria-label="Para revisar">${htmlLista(raiz, d)}</section>
    </div>
    <section class="re-panel re-lower" aria-label="El costo del mes">${htmlCosto(d)}</section>
    ${metodo(raiz)}`;
  sincronizar(raiz);
}

function sincronizar(raiz) {
  const d = raiz.__datos, haySerie = !!d.diario?.actual, esVenta = raiz.__kpi === 'venta';
  if (!esVenta || !haySerie) raiz.__escala = 'anio';
  raiz.querySelectorAll('[data-kpi]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.kpi === raiz.__kpi)));
  raiz.querySelectorAll('[data-escala]').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.escala === raiz.__escala));
    if (b.dataset.escala === 'mes') {
      b.disabled = !(esVenta && haySerie);
      b.title = b.disabled ? 'El detalle día por día es de la venta' : '';
    }
  });
  const modo = raiz.querySelector('.re-seg-modo');
  if (modo) modo.hidden = !(esVenta && raiz.__escala === 'mes' && haySerie);
  raiz.querySelectorAll('[data-modo]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.modo === 'diario') === (raiz.__modo === 'diario'))));
}

function enlazar(raiz) {
  raiz.addEventListener('click', ev => {
    const t = ev.target.closest('button');
    if (!t || !raiz.contains(t) || t.disabled) return;
    const comp = raiz.__componente;
    if (t.dataset.kpi) {
      raiz.__kpi = t.dataset.kpi;
      if (raiz.__kpi === 'venta' && raiz.__datos.diario?.actual) raiz.__escala = raiz.__escalaVenta || 'mes';
      sincronizar(raiz); dibujarGrafico(raiz);
    } else if (t.dataset.escala) {
      raiz.__escala = t.dataset.escala;
      if (raiz.__kpi === 'venta') raiz.__escalaVenta = raiz.__escala;
      sincronizar(raiz); dibujarGrafico(raiz);
    } else if (t.dataset.modo) {
      raiz.__modo = t.dataset.modo; sincronizar(raiz); dibujarGrafico(raiz);
    } else if (t.dataset.item != null) {
      const id = t.dataset.item === 'al_dia' ? 'al_dia' : Number(t.dataset.item);
      raiz.__abierto = raiz.__abierto === id ? null : id;
      raiz.querySelectorAll('.re-item-btn').forEach(b => {
        const bid = b.dataset.item === 'al_dia' ? 'al_dia' : Number(b.dataset.item), on = bid === raiz.__abierto;
        b.setAttribute('aria-expanded', String(on)); b.nextElementSibling.hidden = !on;
      });
    } else if (t.dataset.ir) {
      t.disabled = true; t.textContent = 'Abriendo…';
      comp.setTriggerValue('ir', t.dataset.ir);
    } else if (t.dataset.mes) {
      raiz.querySelectorAll('.re-flecha, select').forEach(e => { e.disabled = true; });
      comp.setTriggerValue('mes', t.dataset.mes);
    } else if (t.classList.contains('re-calc')) {
      t.disabled = true; t.textContent = 'Calculando…';
      comp.setTriggerValue('calcular', true);
    } else if (t.classList.contains('re-ver-pend')) {
      document.querySelector('.st-key-res_sec_pendientes')?.scrollIntoView({block: 'start', behavior: 'smooth'});
    }
  });
  raiz.addEventListener('change', ev => {
    if (ev.target.tagName !== 'SELECT') return;
    ev.target.disabled = true;
    raiz.__componente.setTriggerValue('mes', ev.target.value);
  });
  raiz.addEventListener('toggle', ev => {
    if (ev.target.classList?.contains('re-method')) raiz.__contextoAbierto = ev.target.open;
  }, true);
}

export default function(component) {
  const {parentElement, data} = component;
  let raiz = parentElement.querySelector('.re');
  if (!raiz) {
    raiz = document.createElement('div'); raiz.className = 're'; parentElement.appendChild(raiz);
    raiz.__kpi = 'venta'; raiz.__escala = 'mes'; raiz.__modo = 'acumulado'; raiz.__abierto = null;
    enlazar(raiz);
  }
  raiz.__componente = component;
  // Otro mes es otra lista: lo abierto de la anterior no se arrastra.
  if (raiz.__datos?.mes !== data.mes) raiz.__abierto = null;
  raiz.__datos = data;
  render(raiz, data);
  const observer = new ResizeObserver(() => { dibujarSparks(raiz); dibujarGrafico(raiz); });
  observer.observe(raiz.querySelector('.re-chart'));
  observer.observe(raiz.querySelector('.re-kpis'));
  dibujarSparks(raiz); dibujarGrafico(raiz);
  return () => observer.disconnect();
}
