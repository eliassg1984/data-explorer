// La tabla del costo de ventas del reporte «Costos» (regla #622).
//
// La monta graficos/costos.py con st.components.v2 (sin iframe, estilos en
// un shadow root). Todo lo que pasa acá adentro es del navegador: elegir
// familias, sumar Eventos y Venta interna, añadir salidas, abrir una fila.
// Nada vuelve a Python: la tabla no recalcula la página.
//
// Python manda en `data` lo que arma `costo_ventas.armar`: los meses y, por
// fila, una serie por familia («cubeta»). Las cuentas de abajo (consumo
// operativo, consumo carta, margen, %) se hacen acá porque dependen de lo
// que se elige en pantalla; sus definiciones son las de costo_ventas.py.

const BUCK = ['Alimentos', 'Bebidas', 'Vinos', 'Envases'];
const COLOR = { Alimentos: '--serie-0', Bebidas: '--serie-3', Vinos: '--serie-2', Envases: '--serie-1' };
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const VENTANA = 12;
const BAJAS = 'Bajas';

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }

function etiquetaMes(p) { const [y, m] = p.split('-'); return `${MES[+m - 1]} ${y.slice(2)}`; }
function fechaCorta(s) { const [, m, d] = s.split('-'); return `${+d} ${MES[+m - 1]}`; }
function soles(v) {
  if (v == null || !isFinite(v)) return '—';
  return `${v < -0.5 ? '−' : ''}S/ ${Math.abs(Math.round(v)).toLocaleString('en-US')}`;
}
function num(v) {
  if (v == null || !isFinite(v)) return '—';
  return `${v < -0.5 ? '−' : ''}${Math.abs(Math.round(v)).toLocaleString('en-US')}`;
}
const pct = (v) => (v == null || !isFinite(v) ? '—' : `${(v * 100).toFixed(1)}%`);
const pp = (v) => (v == null || !isFinite(v) ? '—' : `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(1)} pp`);
const mil = (v) => `${(v / 1000).toLocaleString('en-US', { maximumFractionDigits: 1 })} mil`;

// ── Las series de la ventana ─────────────────────────────────────────────
// `st.ini` es el primer mes visible: la tabla muestra VENTANA meses.
function ventana(st, data) {
  const n = data.meses.length;
  const ini = Math.max(0, Math.min(st.ini, n - VENTANA));
  const fin = Math.min(n, ini + VENTANA);
  return { ini, fin, meses: data.meses.slice(ini, fin) };
}

function cortar(arr, w) { return (arr || []).slice(w.ini, w.fin); }
function ceros(w) { return new Array(w.fin - w.ini).fill(0); }
const suma = (a, b) => a.map((x, i) => x + b[i]);
const resta = (a, b) => a.map((x, i) => x - b[i]);

function porFamilia(st, data, w, b) {
  const de = (obj) => (obj && obj[b] ? cortar(obj[b], w) : ceros(w));
  const f = data.filas;
  const r = {
    v: de(f.venta), ii: de(f.inv_inicial), c: de(f.compras), fi: de(f.inv_final),
    bajas: de((data.salidas || {})[BAJAS]), cort: de(f.cortesias), pos: de(f.costo_pos),
  };
  if (st.extra && b === 'Alimentos') {
    for (const g of Object.keys(data.venta_extra || {})) {
      r.v = suma(r.v, cortar(data.venta_extra[g], w));
      r.pos = suma(r.pos, cortar((data.costo_extra || {})[g], w));
    }
  }
  r.operativo = resta(suma(r.ii, r.c), r.fi);
  let carta = resta(resta(r.operativo, r.bajas), r.cort);
  for (const t of st.agregadas) {
    r[`s_${t}`] = de((data.salidas || {})[t]);
    carta = resta(carta, r[`s_${t}`]);
  }
  r.carta = carta;
  r.margen = resta(r.v, r.carta);
  r.dif = resta(r.carta, r.pos);
  return r;
}

function filas(st) {
  const f = [
    // La venta arriba, como en un estado de resultados: es la base de cada %.
    { k: 'v', nom: 'Venta neta', tipo: 'suma', sentido: 'bien', calc: true },
    { k: 'ii', nom: 'Inventario inicial', tipo: 'ini', sentido: 'neutro', fuerte: true },
    { k: 'c', nom: 'Compras', signo: '+', tipo: 'suma', sentido: 'mal' },
    { k: 'fi', nom: 'Inventario final', signo: '−', tipo: 'fin', sentido: 'neutro' },
    { k: 'bajas', nom: 'Bajas', signo: '−', tipo: 'suma', sentido: 'mal' },
    { k: 'cort', nom: 'Costo de cortesías', signo: '−', tipo: 'suma', sentido: 'mal' },
  ];
  for (const t of st.agregadas) f.push({ k: `s_${t}`, nom: t, signo: '−', tipo: 'suma', sentido: 'mal', quitar: t });
  f.push({ agregar: true });
  // El operativo va DESPUÉS de las salidas pero no las resta: es el dato de
  // antes, como en la planilla del usuario.
  f.push({ k: 'operativo', nom: 'Consumo operativo', nota: 'sin restar salidas', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true });
  f.push({ k: 'p_operativo', nom: '% costo operativo', tipo: 'pct', sentido: 'mal', num: 'operativo', den: 'v' });
  f.push({ k: 'carta', nom: 'Consumo carta', nota: 'menos salidas y cortesías', signo: '=', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true });
  f.push({ k: 'p_carta', nom: '% costo carta real', tipo: 'pct', sentido: 'mal', num: 'carta', den: 'v', calc: true });
  f.push({ k: 'margen', nom: 'Margen bruto', nota: 'venta − consumo carta', signo: '=', tipo: 'suma', sentido: 'bien', calc: true, fuerte: true });
  f.push({ sec: 'Contra el Sistema Restaurante (Paloteo comparativo)' });
  f.push({ k: 'pos', nom: 'Costo según Sistema Restaurante', tipo: 'suma', sentido: 'mal' });
  f.push({ k: 'p_pos', nom: '% costo según Sistema Restaurante', tipo: 'pct', sentido: 'mal', num: 'pos', den: 'v' });
  f.push({ k: 'dif', nom: 'Diferencia', nota: 'consumo carta − Sistema Restaurante', signo: '=', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true });
  f.push({ k: 'p_dif', nom: 'Diferencia en puntos', tipo: 'pp', sentido: 'mal', calc: true });
  return f;
}

// Valores de una fila para un conjunto de familias: por mes y el total.
function valores(st, data, w, fila, fams) {
  const R = fams.map((b) => porFamilia(st, data, w, b));
  const sumK = (k) => R.reduce((a, r) => suma(a, r[k]), ceros(w));
  const tot = (a) => a.reduce((x, y) => x + y, 0);
  if (fila.tipo === 'pct') {
    const n = sumK(fila.num), d = sumK(fila.den);
    return { mes: n.map((x, i) => (d[i] ? x / d[i] : null)), tot: tot(d) ? tot(n) / tot(d) : null };
  }
  if (fila.tipo === 'pp') {
    const c = valores(st, data, w, { tipo: 'pct', num: 'carta', den: 'v' }, fams);
    const p = valores(st, data, w, { tipo: 'pct', num: 'pos', den: 'v' }, fams);
    return {
      mes: c.mes.map((x, i) => (x == null || p.mes[i] == null ? null : x - p.mes[i])),
      tot: c.tot == null || p.tot == null ? null : c.tot - p.tot,
    };
  }
  const m = sumK(fila.k);
  const n = m.length;
  // Inventarios: el total de la ventana es su punta, no una suma.
  return { mes: m, tot: fila.tipo === 'ini' ? m[0] : fila.tipo === 'fin' ? m[n - 1] : tot(m) };
}

function fmtCelda(fila, v) {
  if (fila.tipo === 'pct') return pct(v);
  if (fila.tipo === 'pp') return pp(v);
  return num(v);
}
function claseCelda(fila, v) {
  if (v == null) return 'cero';
  if (fila.tipo === 'suma' && Math.abs(v) < 0.5) return 'cero';
  if ((fila.k === 'margen' || fila.k === 'v') && v < 0) return 'neg';
  return '';
}
function sentidoVar(fila, delta) {
  if (fila.sentido === 'neutro' || Math.abs(delta) < 1e-9) return 'neutro';
  const sube = delta > 0;
  return (fila.sentido === 'mal') === sube ? 'mal' : 'bien';
}

// ── Dibujo ───────────────────────────────────────────────────────────────
function dibujar(raiz) {
  const st = raiz.__st, data = st.data;
  if (!data || !data.meses || !data.meses.length) { raiz.innerHTML = ''; return; }
  const w = ventana(st, data);
  st.ini = w.ini;
  const F = BUCK.filter((b) => st.fams.has(b));
  const n = w.meses.length;

  // Cabecera y controles
  const hayMas = data.meses.length > VENTANA;
  let html = `<div class="cv-cab"><h2>Estado de costo de ventas</h2>
    <span class="cv-rango">${etiquetaMes(w.meses[0])} – ${etiquetaMes(w.meses[n - 1])} · ${n} meses operativos</span>
    ${hayMas ? `<span class="cv-ventana"><button type="button" data-ventana="-1" aria-label="Meses anteriores" ${w.ini === 0 ? 'disabled' : ''}>‹</button><button type="button" data-ventana="1" aria-label="Meses siguientes" ${w.fin >= data.meses.length ? 'disabled' : ''}>›</button></span>` : ''}
    </div>`;
  html += `<div class="cv-controles"><div class="cv-grupo"><span class="cv-rot">Familias</span>${BUCK.map((b) =>
    `<button type="button" class="chip" data-fam="${b}" aria-pressed="${st.fams.has(b)}"><span class="pt" style="background:var(${COLOR[b]})"></span>${b}</button>`).join('')}</div>
    <label class="interruptor"><input type="checkbox" data-extra ${st.extra ? 'checked' : ''}> Sumar Eventos y Venta interna a la venta</label></div>`;

  // Resumen de la ventana
  const T = (k) => valores(st, data, w, { k, tipo: 'suma' }, F).tot;
  const v = T('v'), op = T('operativo'), ca = T('carta'), po = T('pos'), mg = T('margen');
  const tiles = [
    ['Venta neta', soles(v), `${n} meses`],
    ['Consumo operativo', soles(op), v ? `${pct(op / v)} costo operativo` : 'sin venta en estas familias'],
    ['Consumo carta', soles(ca), v ? `${pct(ca / v)} costo carta real` : 'sin venta en estas familias', true],
    ['Costo según Sistema Restaurante', soles(po), v ? `${pct(po / v)} de la venta` : '—'],
    ['Diferencia', soles(ca - po), v ? `${pp((ca - po) / v)} sobre la venta` : '—'],
    ['Margen bruto', soles(mg), v ? `${pct(mg / v)} de la venta` : '—'],
  ];
  html += `<div class="cv-resumen">${tiles.map(([k, val, s, foco]) =>
    `<div class="dato${foco ? ' foco' : ''}"><span class="k">${k}</span><span class="v">${val}</span><span class="s">${s}</span></div>`).join('')}</div>`;

  // La tabla
  const cols = `<col class="c-lab">${w.meses.map(() => '<col class="c-mes">').join('')}<col class="c-tot">`;
  const ths = w.meses.map((p) => {
    const fechas = Object.values((data.cierres || {})[p] || {}).map((x) => x[0]).sort();
    let sub = '';
    if (fechas.length) {
      const a = fechaCorta(fechas[0]), z = fechaCorta(fechas[fechas.length - 1]);
      sub = `cierre ${a === z ? a : `${a.split(' ')[0]}–${z}`}`;
    }
    return `<th scope="col">${etiquetaMes(p)}<span class="sub">${sub}</span></th>`;
  }).join('');
  let cuerpo = '';
  for (const fila of filas(st)) {
    if (fila.sec) { cuerpo += `<tr class="sec"><td class="lab">${fila.sec}</td><td colspan="${n + 1}"></td></tr>`; continue; }
    if (fila.agregar) { cuerpo += filaAgregar(st, data, w, F, n); continue; }
    const val = valores(st, data, w, fila, F);
    const abierta = st.abierta === fila.k;
    const cls = ['fila', fila.calc ? 'calc' : '', fila.fuerte ? 'fuerte' : '', abierta ? 'abierta' : ''].join(' ');
    const nota = fila.nota ? ` <span class="nota-fila">${fila.nota}</span>` : '';
    cuerpo += `<tr class="${cls}"><td class="lab"><div class="fila-lab">`
      + `<button type="button" class="fila-btn" data-fila="${esc(fila.k)}" aria-expanded="${abierta}"><span class="signo">${fila.signo || ''}</span>`
      + `<span class="nom${fila.nota ? ' con-nota' : ''}">${esc(fila.nom)}${nota}</span><span class="flecha">▼</span></button>`
      + (fila.quitar ? `<button type="button" class="quitar" data-quitar="${esc(fila.quitar)}" aria-label="Quitar ${esc(fila.quitar)}">×</button>` : '')
      + `</div></td>${val.mes.map((x) => `<td class="${claseCelda(fila, x)}">${fmtCelda(fila, x)}</td>`).join('')}`
      + `<td class="tot ${claseCelda(fila, val.tot)}">${fmtCelda(fila, val.tot)}</td></tr>`;
    if (abierta) cuerpo += detalle(st, data, w, fila, F, val);
  }
  html += `<div class="desliza"><table><colgroup>${cols}</colgroup><thead><tr><th class="lab" scope="col">Concepto<span class="sub">mes operativo</span></th>${ths}<th class="tot" scope="col">${n} meses<span class="sub">${etiquetaMes(w.meses[0])} – ${etiquetaMes(w.meses[n - 1])}</span></th></tr></thead><tbody>${cuerpo}</tbody></table></div>`;
  html += notas(data, w);

  const sx = raiz.querySelector('.desliza') ? raiz.querySelector('.desliza').scrollLeft : 0;
  raiz.innerHTML = html;
  const d = raiz.querySelector('.desliza');
  if (d) d.scrollLeft = sx;
}

function filaAgregar(st, data, w, F, n) {
  const totalDe = (t) => F.reduce((a, b) => a + cortar(((data.salidas || {})[t] || {})[b], w).reduce((x, y) => x + y, 0), 0);
  const disp = Object.keys(data.salidas || {})
    .filter((t) => t !== BAJAS && !st.agregadas.includes(t) && Math.abs(totalDe(t)) > 0.5);
  let menu = '';
  if (st.menu && disp.length) {
    menu = `<div class="menu">${disp.map((t) =>
      `<button type="button" class="chip" data-agregar="${esc(t)}">${esc(t)} <span class="n">S/ ${mil(totalDe(t))}</span></button>`).join('')}</div>`;
  }
  const btn = disp.length
    ? `<button type="button" class="btn-agregar" data-menu>${st.menu ? 'Cerrar' : '+ Añadir otra salida'}</button>`
    : '<span class="cero">No hay otras salidas en estos meses.</span>';
  return `<tr class="agregar"><td colspan="${n + 2}">${btn}${menu}</td></tr>`;
}

function detalle(st, data, w, fila, F, val) {
  const n = val.mes.length;
  const esPct = fila.tipo === 'pct' || fila.tipo === 'pp';
  const fmt = (x) => (esPct ? fmtCelda(fila, x) : soles(x));
  const series = st.modo === 'total'
    ? [{ nom: 'Total', vals: val.mes, color: 'var(--accent)' }]
    : F.map((b) => ({ nom: b, vals: valores(st, data, w, fila, [b]).mes, color: `var(${COLOR[b]})` }))
      .filter((s) => s.vals.some((x) => x != null && Math.abs(x) > 5e-4));
  const todos = series.flatMap((s) => s.vals).filter((x) => x != null && isFinite(x));
  let lo = todos.length ? Math.min(...todos) : 0, hi = todos.length ? Math.max(...todos) : 1;
  if (hi - lo < 1e-9) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.14; lo -= pad; hi += pad;
  const y = (x) => 100 - ((x - lo) / (hi - lo)) * 100;
  const xp = (i) => (i + 0.5) * 100;

  let svg = `<svg viewBox="0 0 ${n * 100} 100" preserveAspectRatio="none" aria-hidden="true">`;
  for (const g of [25, 50, 75]) svg += `<line x1="0" x2="${n * 100}" y1="${g}" y2="${g}" stroke="var(--border-lavender)" stroke-width="1" vector-effect="non-scaling-stroke" opacity=".6"/>`;
  if (lo < 0 && hi > 0) svg += `<line x1="0" x2="${n * 100}" y1="${y(0)}" y2="${y(0)}" stroke="var(--text-secondary)" stroke-width="1" vector-effect="non-scaling-stroke"/>`;
  let puntos = '';
  for (const s of series) {
    const pts = s.vals.map((x, i) => (x == null ? null : `${xp(i)},${y(x)}`)).filter(Boolean);
    if (st.modo === 'total' && pts.length > 1) {
      const base = lo < 0 && hi > 0 ? y(0) : 100;
      svg += `<polygon points="${xp(0)},${base} ${pts.join(' ')} ${xp(n - 1)},${base}" fill="var(--accent)" opacity=".10"/>`;
      const vs = s.vals.filter((x) => x != null);
      const prom = vs.reduce((a, x) => a + x, 0) / vs.length;
      svg += `<line x1="0" x2="${n * 100}" y1="${y(prom)}" y2="${y(prom)}" stroke="var(--accent)" stroke-dasharray="4 4" stroke-width="1" vector-effect="non-scaling-stroke" opacity=".7"/>`;
    }
    svg += `<polyline points="${pts.join(' ')}" fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
    if (st.modo === 'total') {
      s.vals.forEach((x, i) => {
        if (x == null) return;
        const prev = i > 0 ? s.vals[i - 1] : null;
        const sv = prev == null ? 'neutro' : sentidoVar(fila, x - prev);
        const col = sv === 'mal' ? 'var(--danger-text)' : sv === 'bien' ? 'var(--success-text)' : 'var(--accent)';
        puntos += `<div class="hitbox" style="left:calc(${i} * 100% / ${n});width:calc(100% / ${n})"></div>`
          + `<div class="punto${i === n - 1 ? ' ult' : ''}" style="left:calc(${i + 0.5} * 100% / ${n});top:${y(x)}%;background:${col}"><span class="tip">${fmt(x)}</span></div>`;
      });
    }
  }
  svg += '</svg>';

  // Una sola marca de variación: la del mes contra el anterior.
  let vari;
  if (st.modo === 'total') {
    vari = `<div class="variaciones" style="grid-template-columns:repeat(${n},1fr)">${val.mes.map((x, i) => {
      const prev = i > 0 ? val.mes[i - 1] : null;
      if (prev == null || x == null) return `<span class="neutro">${i === 0 ? '' : '—'}</span>`;
      const dlt = x - prev;
      let t;
      if (esPct) t = `${dlt >= 0 ? '▲' : '▼'} ${Math.abs(dlt * 100).toFixed(1)} pp`;
      else if (Math.abs(prev) < 1) t = '—';
      else t = `${dlt >= 0 ? '▲' : '▼'} ${Math.abs((dlt / Math.abs(prev)) * 100).toFixed(0)}%`;
      return `<span class="${sentidoVar(fila, dlt)}">${t}</span>`;
    }).join('')}</div>`;
  } else {
    vari = `<div class="leyenda">${series.map((s) => `<span><i style="background:${s.color}"></i>${s.nom}</span>`).join('')}</div>`;
  }

  const vs = val.mes.map((x, i) => [x, i]).filter(([x]) => x != null);
  const prom = vs.reduce((a, [x]) => a + x, 0) / (vs.length || 1);
  const mn = vs.reduce((a, b) => (b[0] < a[0] ? b : a), vs[0] || [null, 0]);
  const mx = vs.reduce((a, b) => (b[0] > a[0] ? b : a), vs[0] || [null, 0]);
  const ult = val.mes[n - 1];
  let vsProm = '—';
  if (ult != null && prom) {
    vsProm = esPct ? pp(ult - prom)
      : `${ult - prom >= 0 ? '+' : '−'}${Math.abs(((ult - prom) / Math.abs(prom)) * 100).toFixed(0)}%`;
  }
  const stats = `<div class="stats">
      <span>Promedio <b>${fmt(prom)}</b></span>
      <span>Mínimo <b>${fmt(mn[0])}</b> · ${etiquetaMes(w.meses[mn[1]])}</span>
      <span>Máximo <b>${fmt(mx[0])}</b> · ${etiquetaMes(w.meses[mx[1]])}</span>
      <span>${etiquetaMes(w.meses[n - 1])} contra el promedio <b>${vsProm}</b></span>
      <div class="modo" role="group" aria-label="Qué dibujar">
        <button type="button" data-modo="total" aria-pressed="${st.modo === 'total'}">Total</button>
        <button type="button" data-modo="familia" aria-pressed="${st.modo === 'familia'}">Por familia</button>
      </div></div>`;

  // La columna del total: de qué familias se compone la fila.
  let comp = '';
  if (F.length > 1) {
    const partes = F.map((b) => ({ b, t: valores(st, data, w, fila, [b]).tot }))
      .filter((p) => p.t != null && isFinite(p.t) && (esPct || Math.abs(p.t) > 0.5));
    if (esPct) {
      comp = `<div class="comp">${partes.map((p) => `<div class="fila-c"><span>${p.b}</span><b>${fmtCelda(fila, p.t)}</b></div>`).join('')}</div>`;
    } else if (partes.length && partes.every((p) => p.t >= 0)) {
      const total = partes.reduce((a, p) => a + p.t, 0);
      comp = `<div class="comp"><div class="barra">${partes.map((p) => `<span style="width:${(p.t / total) * 100}%;background:var(${COLOR[p.b]})"></span>`).join('')}</div>`
        + `${partes.map((p) => `<div class="fila-c"><span>${p.b}</span><b>${Math.round((p.t / total) * 100)}%</b></div>`).join('')}</div>`;
    }
  }
  return `<tr class="detalle"><td class="lab">${stats}</td><td colspan="${n}" class="graf-celda"><div class="graf">${svg}${puntos}</div>${vari}</td><td class="tot">${comp}</td></tr>`;
}

function notas(data, w) {
  const tot = (arr) => cortar(arr, w).reduce((a, x) => a + x, 0);
  const vEx = data.venta_extra || {}, cEx = data.costo_extra || {};
  const ev = 'Eventos', vi = 'Venta interna';
  return `<div class="notas">
  <details class="nota"><summary>De dónde sale cada fila</summary><dl>
    <dt>Venta neta</dt><dd>Sin IGV ni recargo, sin cortesías ni anulados, con las notas de crédito restando, por día del turno de caja. Grupos Alimentos, Bebidas con alcohol, sin alcohol y calientes, y Vinos y Espumantes.</dd>
    <dt>Inventario inicial y final</dt><dd>El cierre de inventario de cada área en su mes operativo: el que se registra del 1 al 6 cuenta para el mes anterior. Se toma el último cierre de cada área en el mes, valorizado como se contó (stock declarado × precio promedio). El inicial de un mes es el final del anterior. Alimentos, Bebidas, Vinos y Envases.</dd>
    <dt>Compras</dt><dd>Valor neto, sin IGV, con las notas de crédito de los proveedores restadas, por fecha del documento.</dd>
    <dt>Bajas y las otras salidas</dt><dd>Notas de salida procesadas, a su valor neto, por fecha de registro, como la «Relación de Notas de Salidas» del Almacén.</dd>
    <dt>Costo de cortesías</dt><dd>Lo que el Sistema Restaurante facturó como cortesía en Alimentos, Bebidas y Vinos, a precio costo. Se resta porque su costo, «(a) Ventas en el rango», no las incluye: en el Paloteo son otro origen, «(b) Cortesías».</dd>
    <dt>Consumo operativo y consumo carta</dt><dd>Consumo operativo = inventario inicial + compras − inventario final: todo lo que salió del almacén, sin restar salidas ni cortesías; no se compara con el Sistema Restaurante. Consumo carta = consumo operativo − bajas − cortesías − las otras salidas que se añadan: lo que costó lo vendido, y es el que se compara con el Sistema Restaurante.</dd>
    <dt>Costo según Sistema Restaurante</dt><dd>El costo a precio costo de lo vendido en esos grupos: lo del Paloteo de Producción, tipo Comparativo, con origen «(a) Ventas en el rango». El Paloteo fecha por la apertura de la mesa y esta tabla por el turno: un pedido de medianoche del último día puede caer en otro mes.</dd>
  </dl></details>
  <details class="nota alerta"><summary>Antes de leer la diferencia</summary><ul>
    <li><b>Envases entra en inventario, compras y salidas, pero el Sistema Restaurante no lo costea.</b> Para comparar en igualdad, desmarcá Envases.</li>
    <li><b>Eventos y Venta interna gastan inventario y no están en la venta.</b> En estos meses vendieron S/ ${mil(tot(vEx[ev]))} y S/ ${mil(tot(vEx[vi]))}, con un costo de S/ ${mil(tot(cEx[ev]))} y S/ ${mil(tot(cEx[vi]))}. Fuera de la venta, su consumo agranda la diferencia; el interruptor los suma a Alimentos.</li>
    <li><b>Costos de producción queda fuera</b> de inventarios, compras y salidas.</li>
    <li><b>Desde octubre 2025.</b> Antes, los cierres y el kardex no cuadran (setiembre 2025 tuvo un ajuste de S/ 627 mil al limpiar el inventario).</li>
  </ul></details></div>`;
}

// ── Eventos: uno solo en la raíz, que sobrevive a cada dibujo ──────────
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const st = raiz.__st;
    const b = ev.target.closest('button');
    if (!b || !raiz.contains(b)) return;
    if (b.dataset.fam) {
      const f = b.dataset.fam;
      if (st.fams.has(f)) { if (st.fams.size > 1) st.fams.delete(f); } else st.fams.add(f);
      guardar('costos_fams', [...st.fams]);
    } else if (b.dataset.fila) {
      st.abierta = st.abierta === b.dataset.fila ? null : b.dataset.fila;
      st.modo = 'total';
    } else if (b.dataset.quitar) {
      st.agregadas = st.agregadas.filter((t) => t !== b.dataset.quitar);
      if (st.abierta === `s_${b.dataset.quitar}`) st.abierta = null;
      guardar('costos_salidas', st.agregadas);
    } else if (b.dataset.agregar) {
      st.agregadas.push(b.dataset.agregar);
      st.menu = false;
      guardar('costos_salidas', st.agregadas);
    } else if (b.hasAttribute('data-menu')) {
      st.menu = !st.menu;
    } else if (b.dataset.modo) {
      st.modo = b.dataset.modo;
    } else if (b.dataset.ventana) {
      st.ini += Number(b.dataset.ventana) * VENTANA;
    } else {
      return;
    }
    dibujar(raiz);
  });
  raiz.addEventListener('change', (ev) => {
    if (ev.target.matches('[data-extra]')) {
      raiz.__st.extra = ev.target.checked;
      guardar('costos_extra', raiz.__st.extra);
      dibujar(raiz);
    }
  });
}

export default function (component) {
  const { data, parentElement } = component;
  let raiz = parentElement.querySelector('.cv');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'cv';
    parentElement.appendChild(raiz);
    const fams = leer('costos_fams', BUCK).filter((b) => BUCK.includes(b));
    raiz.__st = {
      fams: new Set(fams.length ? fams : BUCK),
      extra: leer('costos_extra', false) === true,
      agregadas: leer('costos_salidas', []).filter((t) => typeof t === 'string' && t !== BAJAS),
      abierta: null, modo: 'total', menu: false, ini: Number.MAX_SAFE_INTEGER,
    };
    enlazar(raiz);
  }
  const st = raiz.__st;
  st.data = data || {};
  // Una salida guardada que estos datos no traen no se dibuja.
  st.agregadas = st.agregadas.filter((t) => (st.data.salidas || {})[t]);
  dibujar(raiz);
}
