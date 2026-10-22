// Ventas › «Mix de carta» (regla #702).
//
// La monta graficos/ventas_mix.py::_ventas_mix con st.components.v2 (sin
// iframe, estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/7V1JFc8uhBouVgd4dXkR8T): los indicadores, los
// controles, la barra por período con su leyenda, la ficha de lo elegido y
// las cinco pestañas (Resumen, Qué movió, Mapa, Mix y costo, Cálculo).
// Python manda las sumas por producto y período; todo lo demás se resuelve
// acá sin una corrida. Vuelven a Python: `gran` (otra granularidad), `ap`
// (traer el año pasado), `lineas` (Cálculo de un producto, venta por venta)
// y `carta` (el salto a Costo de Carta).
//
// LAS CUENTAS SON LAS DE ventas_mix.py: `pctCosto` es `pct_costo` (costo ÷
// base, sin cociente donde no hay costo o la base no llega a medio sol),
// `tramos` es `tramos` (siete con color y «Resto (N)», nunca «Resto (1)»),
// y el Cálculo suma lo mismo que `calculo`. El test busca las fórmulas
// escritas igual.
//
// Python manda en `data`: `gran`, `grans`, `periodos` ([{clave, eje,
// largo, parcial, igv}]), `prods` ([grupo, subgrupo, nombre, área]),
// `codigos` (uno por producto, para Costo de Carta), `filas` ([producto,
// período, V, Q, C, B, NC, SC, IGV, REC, DESC, DEV]), `ap` (null o {filas,
// nombres}: la misma forma, con el período de ESTE rango con el que se
// compara cada fila), `lineas`, `nota`, `hay_area`, `niveles`, `umbrales`
// ([0.45, 0.70]), `tramos` (7) y `ayuda`.

const CLAVE = 'vt_mix_est';
const V = 0, Q = 1, C = 2, B = 3, NC = 4, SC = 5, IGV = 6, REC = 7, DESC = 8, DEV = 9;
const NM = 10;
const COLOR = (k) => `var(--serie-${k})`;
const RESTO = 'var(--scroll-thumb)';
const NETO_MIN = 0.5;

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const fk = (v) => { const a = Math.abs(v), s = v < 0 ? '−' : ''; if (a >= 1e6) return `${s}S/ ${(a / 1e6).toFixed(2)}M`; if (a >= 1e3) return `${s}S/ ${(a / 1e3).toFixed(1)}k`; return `${s}S/ ${a.toFixed(0)}`; };
const fs = (v) => `${v < -0.005 ? '−' : ''}${Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fn = (v) => Math.round(v).toLocaleString('en-US');
const pc = (v, d = 1) => (v == null || !isFinite(v) ? '—' : `${(v * 100).toFixed(d)}%`);
const conSigno = (v, txt) => (v > 1e-9 ? '+' : v < -1e-9 ? '−' : '') + txt;
const pp = (v, d = 1) => conSigno(v, `${Math.abs(v * 100).toFixed(d)} pp`);
const varPct = (a, b) => (b > 0 ? a / b - 1 : NaN);
const cap1 = (s) => String(s).charAt(0).toUpperCase() + String(s).slice(1);

// ── Las cuentas de ventas_mix.py ─────────────────────────────────────────
function pctCosto(costo, base) {
  // `pct_costo`: sin costo cargado no hay %, y una base que no llega a
  // medio sol (una cortesía a S/ 0, una nota en otro período) tampoco.
  return costo > 0 && base > NETO_MIN ? costo / base : NaN;
}
function tramos(orden, max) {
  // `tramos`: `max` con color y el resto junto; con `max` + 1, todos.
  if (orden.length <= max + 1) return orden.map((n) => [n, [n], false]);
  const resto = orden.slice(max);
  return orden.slice(0, max).map((n) => [n, [n], false]).concat([[`Resto (${resto.length})`, resto, true]]);
}
const nivelCosto = (d, p) => (!isFinite(p) ? '' : p > d.umbrales[1] ? 'c-roto' : p > d.umbrales[0] ? 'c-alto' : '');

// ── Sumas ────────────────────────────────────────────────────────────────
function clave(d, st, pi, lvl) { return lvl === 0 ? (st.eje === 'Área' ? d.prods[pi][3] : d.prods[pi][0]) : d.prods[pi][lvl]; }
function enRuta(d, st, pi, ruta) { for (let k = 0; k < ruta.length; k++) if (clave(d, st, pi, k) !== ruta[k]) return false; return true; }
function acum(d, st, filas, keyFn, ruta, np) {
  const m = new Map();
  for (const r of filas) {
    if (!enRuta(d, st, r[0], ruta)) continue;
    const k = keyFn(r[0]);
    let a = m.get(k);
    if (!a) { a = new Float64Array(np * NM); m.set(k, a); }
    const o = r[1] * NM;
    for (let j = 0; j < NM; j++) a[o + j] += r[2 + j];
  }
  return m;
}
function total(m, np) { const t = new Float64Array(np * NM); for (const a of m.values()) for (let j = 0; j < t.length; j++) t[j] += a[j]; return t; }
const en = (a, i, j) => (a ? a[i * NM + j] : 0);
const sumT = (a, T, j) => { let s = 0; for (const i of T) s += en(a, i, j); return s; };
const enPer = (a, i) => (a ? Array.from(a.subarray(i * NM, i * NM + NM)) : new Array(NM).fill(0));

// ── Estado derivado ──────────────────────────────────────────────────────
function calcular(raiz) {
  const { data: d, st } = raiz.__d;
  const np = d.periodos.length, todos = d.periodos.map((_, i) => i);
  if (st.eje === 'Área' && !d.hay_area) st.eje = 'Carta';
  const niv = d.niveles[st.eje];
  // El nivel por NOMBRE: si un nombre ya no existe (otro rango, otro eje),
  // se recorta la ruta.
  while (st.ruta.length && !d.filas.some((r) => enRuta(d, st, r[0], st.ruta))) st.ruta.pop();
  const ruta = st.ruta, lvl = ruta.length;
  const med = st.medida === 'Unidades' ? Q : V;
  const M = acum(d, st, d.filas, (pi) => clave(d, st, pi, lvl), ruta, np);
  const tot = total(M, np);
  const totLocal = total(acum(d, st, d.filas, () => '·', [], np), np);
  let foco = d.periodos.findIndex((p) => p.clave === st.foco);
  if (foco < 0) { foco = null; st.foco = null; }
  const T = foco !== null ? [foco] : todos;
  const orden = [...M.keys()].filter((k) => todos.some((i) => Math.abs(en(M.get(k), i, V)) > 0.5 || Math.abs(en(M.get(k), i, Q)) > 0.01))
    .sort((a, b) => sumT(M.get(b), todos, med) - sumT(M.get(a), todos, med));
  let ci = 0;
  const tr = tramos(orden, d.tramos).map(([nombre, miembros, resto]) => ({ nombre, miembros, resto, color: resto ? RESTO : COLOR(ci++) }));
  const colorDe = {};
  tr.forEach((t) => t.miembros.forEach((m) => { colorDe[m] = t.color; }));
  const completos = todos.filter((i) => !d.periodos[i].parcial);
  const iDet = foco !== null ? foco : (completos.length ? completos[completos.length - 1] : np - 1);
  if (st.sel !== null && !M.has(st.sel)) st.sel = null;
  raiz.__d.x = { np, todos, niv, ruta, lvl, med, M, tot, totLocal, foco, T, orden, tr, colorDe, iDet };
  return raiz.__d.x;
}
const per = (d) => ({ 'Día': ['día', 'días'], Semana: ['semana', 'semanas'], Mes: ['mes', 'meses'], 'Año': ['año', 'años'] }[d.gran] || ['período', 'períodos']);
const unid = (st) => st.medida === 'Unidades';
const fmed = (st, v) => (unid(st) ? `${fn(v)} und` : fk(v));
function cuando(d, x) { return x.foco !== null ? d.periodos[x.foco].largo : `${x.T.length} ${x.T.length === 1 ? per(d)[0] : per(d)[1]}`; }

// ── Indicadores ──────────────────────────────────────────────────────────
function htmlKpis(d, st, x) {
  const k = (rot, val, sub = '', cls = '', tip = '') =>
    `<div class="vm-kpi ${cls}" title="${esc(tip || rot)}"><span class="vm-kpi-rot">${esc(rot)}</span><span class="vm-kpi-val">${val}${sub ? `<span class="vm-kpi-sub">${esc(sub)}</span>` : ''}</span></div>`;
  const { tot, totLocal, T, foco, ruta } = x;
  const v = sumT(tot, T, V), q = sumT(tot, T, Q), c = sumT(tot, T, C), b = sumT(tot, T, B), nc = sumT(tot, T, NC), sc = sumT(tot, T, SC);
  const h = [k(`Venta · ${cuando(d, x)}`, esc(fk(v)), '', '', `Venta: S/ ${fs(v)}`)];
  if (foco === null) {
    const comp = x.todos.filter((i) => !d.periodos[i].parcial);
    if (comp.length) h.push(k(`Promedio por ${per(d)[0]}`, esc(fk(comp.reduce((s, i) => s + en(tot, i, V), 0) / comp.length)), '', '', 'Sólo períodos completos'));
  } else {
    const p = varEstado(d, x.tot, foco, V);
    h.push(k(`vs ${per(d)[0]} anterior`, p.txt ? `<span class="${p.cls}">${esc(p.txt)}</span>` : '—', '', '', p.tip));
  }
  const pcost = pctCosto(c, b);
  h.push(k('% costo', `<span class="${nivelCosto(d, pcost).replace('c-alto', 'ambar').replace('c-roto', 'rojo')}">${pc(pcost)}</span>`, '', '', d.ayuda.costo));
  h.push(k('% sin desc.', pc(pctCosto(c, nc)), '', '', d.ayuda.sin_desc));
  h.push(k('Margen bruto', esc(fk(b - c)), b > NETO_MIN ? pc((b - c) / b, 0) : '', '', 'Venta neta (+ devolución del banco) − costo, sobre lo que tiene costo cargado'));
  h.push(k('Unidades', fn(q)));
  const prods = new Set();
  for (const r of d.filas) if (T.includes(r[1]) && r[2 + V] > 0.5 && enRuta(d, st, r[0], ruta)) prods.add(d.prods[r[0]][1] + '\u0001' + d.prods[r[0]][2]);
  h.push(k('Productos con venta', fn(prods.size)));
  if (ruta.length) { const vl = sumT(totLocal, T, V); h.push(k('Del total del local', pc(vl ? v / vl : NaN))); }
  if (sc > 0.5) {
    const sin = new Map();
    for (const r of d.filas) if (T.includes(r[1]) && r[2 + SC] > 0.5 && enRuta(d, st, r[0], ruta)) sin.set(d.prods[r[0]][2], (sin.get(d.prods[r[0]][2]) || 0) + r[2 + SC]);
    const lista = [...sin.entries()].sort((a, b2) => b2[1] - a[1]);
    h.push(k('Sin costo cargado', esc(fk(sc)), `${lista.length} prod.`, 'alerta',
      'Vendido sin costo en el POS: no entra en ningún % de costo. ' + lista.slice(0, 6).map(([n, s]) => `${n} S/ ${fn(s)}`).join('; ')));
  }
  return h.join('');
}
function varEstado(d, a, i, j) {
  // La variación contra la barra ANTERIOR, con los estados de `_variaciones`.
  if (d.periodos[i].parcial) return { txt: 'parcial', cls: 'gris', tip: 'El rango corta este período: el monto no se compara parejo' };
  if (i === 0) return { txt: '', cls: 'gris', tip: 'Primer período del rango' };
  if (d.periodos[i - 1].parcial) return { txt: '', cls: 'gris', tip: 'El anterior está cortado por el rango' };
  const p = varPct(en(a, i, j), en(a, i - 1, j));
  if (!isFinite(p)) return { txt: '', cls: 'gris', tip: '' };
  return { txt: (p >= 0 ? '▲ ' : '▼ ') + pc(Math.abs(p)), cls: p >= 0 ? 'verde' : 'rojo', tip: '' };
}

// ── Controles ────────────────────────────────────────────────────────────
function seg(opciones, actual, acc, apagadas = {}) {
  if (!opciones.length) return '';
  return `<div class="vm-seg" role="group">${opciones.map(([val, rot]) => `<button type="button" data-acc="${acc}" data-id="${esc(val)}" class="${val === actual ? 'on' : ''}" ${apagadas[val] ? `disabled title="${esc(apagadas[val])}"` : ''}>${esc(rot)}</button>`).join('')}</div>`;
}
function htmlControles(d, st) {
  const ejes = d.hay_area ? [['Carta', 'Carta'], ['Área', 'Área']] : [['Carta', 'Carta']];
  return `<div class="vm-grupo"><span class="vm-rot">Abrir por</span>${seg(ejes, st.eje, 'eje')}</div>
    <div class="vm-grupo"><span class="vm-rot">Agrupar</span>${seg(d.grans.map((g) => [g, g]), d.gran, 'gran')}</div>
    <div class="vm-grupo"><span class="vm-rot">Medir</span>${seg([['Soles', 'Soles'], ['Unidades', 'Unidades']], st.medida, 'medida')}</div>
    <div class="vm-grupo"><span class="vm-rot">Escala</span>${seg([['Monto', 'Monto'], ['%', '% del período']], st.escala, 'escala')}</div>
    <div class="vm-der"><input class="vm-buscar" data-acc="buscar" list="vm-prods" placeholder="Buscar un producto…" autocomplete="off" aria-label="Buscar un producto"></div>`;
}
function apDisponible(d, i) { return !d.ap || !!d.ap.nombres[i]; }
function htmlPie(d, st, x) {
  const zonas = [['Resumen', 'Resumen'], ['Movio', 'Qué movió'], ['Mapa', 'Mapa'], ['Mix', 'Mix y costo'], ['Calculo', 'Cálculo']];
  const comp = seg([['ant', 'Período anterior'], ['ap', 'Año pasado']], st.comp, 'comp',
    apDisponible(d, x.iDet) ? {} : { ap: 'Sin año pasado para este período: el parquet empieza el 1 de enero de 2025' });
  let extra = '';
  if (st.zona === 'Resumen') extra = seg([['Venta', 'Venta'], ['pct', '% del período'], ['costo', '% costo']], st.celdas, 'celdas');
  else if (st.zona === 'Movio') extra = comp + seg([['Monto', 'Monto'], ['Mix', 'Mix (pp)']], st.cambio, 'cambio');
  else if (st.zona === 'Mix') extra = comp;
  else if (st.zona === 'Mapa') extra = seg([['costo', 'Color: % costo'], ['grupo', `Color: ${x.niv[1][x.lvl]}`]], st.color, 'color');
  return seg(zonas, st.zona, 'zona') + extra + '<div class="vm-cap" data-zona="cap"></div>';
}

// ── Ruta y leyenda ───────────────────────────────────────────────────────
function htmlRuta(d, st, x) {
  const todo = x.niv[2];
  const partes = [x.ruta.length ? `<button type="button" data-acc="subir" data-id="0">${esc(todo)}</button>` : `<b>${esc(todo)}</b>`];
  x.ruta.forEach((n, k) => { partes.push('<span class="sep">›</span>'); partes.push(k === x.ruta.length - 1 ? `<b>${esc(n)}</b>` : `<button type="button" data-acc="subir" data-id="${k + 1}">${esc(n)}</button>`); });
  partes.push(`<span class="pista">${x.foco === null ? 'Tocá una barra para fijar el período' : 'Tocá la barra otra vez para soltarla'}</span>`);
  return partes.join(' ');
}
function htmlLeyenda(d, st, x) {
  const { tr, M, T, tot, lvl, niv } = x;
  const tT = sumT(tot, T, x.med);
  const filas = tr.map((t) => {
    const v = t.miembros.reduce((s, m) => s + sumT(M.get(m), T, x.med), 0);
    const val = `<span class="val">${esc(fmed(st, v))}<small>${pc(tT ? v / tT : NaN, 0)}</small></span>`;
    if (t.resto) return `<div class="vm-li resto" title="${esc(t.miembros.slice(0, 15).join(' · '))}${t.miembros.length > 15 ? ' …' : ''}"><i style="background:${t.color}"></i><span class="nom">${esc(t.nombre)}</span>${val}<span></span></div>`;
    return `<div class="vm-li${st.sel === t.nombre ? ' sel' : ''}" data-acc="sel" data-id="${esc(t.nombre)}"><i style="background:${t.color}"></i><span class="nom" title="${esc(t.nombre)}">${esc(t.nombre)}</span>${val}${lvl < 2 ? `<button type="button" class="vm-bajar" data-acc="bajar" data-id="${esc(t.nombre)}" title="Ver sus ${esc(niv[0][lvl + 1].toLowerCase())}" aria-label="Ver sus ${esc(niv[0][lvl + 1].toLowerCase())}">›</button>` : '<span></span>'}</div>`;
  });
  return `<div class="vm-ley-cab"><span>${esc(niv[0][lvl])}</span><span>${esc(x.foco !== null ? d.periodos[x.foco].eje : cuando(d, x))}</span></div>` + filas.join('');
}

// ── La barra ─────────────────────────────────────────────────────────────
function htmlGrafico(d, st, x, W, H) {
  const { tr, M, tot, todos } = x;
  const mT = 36, mB = 22, mX = 4;
  const n = todos.length, slot = (W - 2 * mX) / Math.max(1, n), bw = Math.max(3, Math.min(54, slot * 0.64));
  const pct = st.escala === '%';
  const vals = todos.map((i) => tr.map((t) => Math.max(0, t.miembros.reduce((s, m) => s + en(M.get(m), i, x.med), 0))));
  const tots = vals.map((r) => r.reduce((s, y) => s + y, 0));
  const max = pct ? 1 : Math.max(1, ...tots);
  const y = (v) => mT + (H - mT - mB) * (1 - v / max);
  // Cuántos rótulos entran: con muchas barras, uno cada tanto.
  const cada = Math.max(1, Math.ceil(46 / slot));
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Venta por período">`;
  for (let k = 1; k <= 3; k++) { const yy = y((max * k) / 4); s += `<line class="g-guia" x1="${mX}" x2="${W - mX}" y1="${yy}" y2="${yy}"/>`; }
  s += `<line class="g-base" x1="${mX}" x2="${W - mX}" y1="${y(0)}" y2="${y(0)}"/>`;
  todos.forEach((i, k) => {
    const cx = mX + slot * (k + 0.5), x0 = cx - bw / 2, on = x.foco === i;
    s += `<g class="g-col${x.foco !== null && !on ? ' apagada' : ''}" data-i="${i}">`;
    if (on) s += `<rect class="g-foco" x="${cx - slot / 2 + 1}" y="2" width="${Math.max(1, slot - 2)}" height="${H - 4}" rx="6"/>`;
    s += `<rect class="g-hit" x="${cx - slot / 2}" y="0" width="${slot}" height="${H}"/>`;
    let acc = 0;
    tr.forEach((t, j) => {
      const v = pct ? (tots[k] ? vals[k][j] / tots[k] : 0) : vals[k][j];
      if (v <= 0) return;
      const y1 = y(acc + v), y0 = y(acc);
      s += `<rect class="t" x="${x0}" y="${y1}" width="${bw}" height="${Math.max(0, y0 - y1 - 0.6)}" style="fill:${t.color}" rx="1.5" data-t="${j}"/>`;
      acc += v;
    });
    if (k % cada === 0 || on) {
      const top = y(pct ? 1 : tots[k]), t = en(tot, i, x.med);
      const ve = varEstado(d, tot, i, x.med);
      s += `<text class="g-tot" x="${cx}" y="${top - 17}" text-anchor="middle">${esc(unid(st) ? fn(t) : fk(t).replace('S/ ', ''))}</text>`;
      if (ve.txt) s += `<text class="g-var ${ve.cls}" x="${cx}" y="${top - 5}" text-anchor="middle">${esc(slot < 44 ? ve.txt.replace(/\.\d%/, '%') : ve.txt)}</text>`;
      s += `<text class="g-eje${on ? ' on' : ''}" x="${cx}" y="${H - 5}" text-anchor="middle">${esc(d.periodos[i].eje)}</text>`;
    }
    s += '</g>';
  });
  return s + '</svg>';
}

// ── La ficha ─────────────────────────────────────────────────────────────
function spark(serie, { foco = null, umbral = null, barras = false, color = 'var(--accent)' }) {
  const W = 256, H = 40, n = serie.length, ok = serie.filter((v) => isFinite(v));
  if (!ok.length) return '<div class="fi-nota">Sin datos.</div>';
  let lo = Math.min(...ok), hi = Math.max(...ok);
  if (umbral !== null) { lo = Math.min(lo, umbral); hi = Math.max(hi, umbral); }
  if (barras) lo = Math.min(0, lo);
  if (hi - lo < 1e-9) { hi += 1; if (!barras) lo -= 1; }
  const px = (k) => 3 + ((W - 6) * (k + 0.5)) / n, py = (v) => 3 + (H - 8) * (1 - (v - lo) / (hi - lo));
  let s = `<svg class="fi-spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">`;
  if (umbral !== null) s += `<line x1="0" x2="${W}" y1="${py(umbral)}" y2="${py(umbral)}" style="stroke:var(--warning)" stroke-dasharray="3 3" stroke-width="1"/>`;
  if (barras) {
    const bw = Math.max(2, ((W - 6) / n) * 0.6);
    serie.forEach((v, k) => { if (!isFinite(v)) return; const yv = py(Math.max(v, 0)); s += `<rect x="${px(k) - bw / 2}" y="${yv}" width="${bw}" height="${Math.max(1, py(0) - yv)}" rx="1.5" style="fill:${k === foco ? 'var(--accent-deep)' : 'var(--accent-light)'}"/>`; });
  } else {
    let dd = '';
    serie.forEach((v, k) => { if (!isFinite(v)) return; dd += `${dd ? 'L' : 'M'}${px(k).toFixed(1)},${py(v).toFixed(1)}`; });
    s += `<path d="${dd}" fill="none" style="stroke:${color}" stroke-width="1.8" stroke-linejoin="round"/>`;
    const kk = foco !== null ? foco : n - 1;
    if (isFinite(serie[kk])) s += `<circle cx="${px(kk)}" cy="${py(serie[kk])}" r="3" style="fill:${color}"/>`;
  }
  return s + '</svg>';
}
function htmlFicha(d, st, x) {
  const { M, tot, totLocal, T, lvl, ruta, niv, iDet, todos, foco } = x;
  const miembro = st.sel !== null;
  const a = miembro ? M.get(st.sel) : tot;
  const base = miembro ? tot : totLocal;
  const nombre = miembro ? st.sel : (ruta.length ? ruta[ruta.length - 1] : 'Todo el local');
  const nivelRot = miembro ? niv[1][lvl] : (ruta.length ? niv[1][ruta.length - 1] : 'local');
  const camino = [niv[2], ...(miembro ? ruta : ruta.slice(0, -1))].join(' › ');
  const enQue = miembro ? (ruta.length ? ruta[ruta.length - 1] : 'el local') : 'el local';
  const kUlt = foco !== null ? foco : todos.length - 1, cUlt = d.periodos[kUlt].eje;
  const v = sumT(a, T, V), vb = sumT(base, T, V);
  let h = `<div class="fi-cab"><span class="fi-nivel">${esc(nivelRot)}</span><span class="fi-nom">${esc(nombre)}</span><span class="fi-ruta">${esc(miembro || ruta.length ? camino : 'Toda la carta')}</span></div>`;
  // El año pasado del período en detalle, si ya se trajo.
  let ap = '';
  const pre = foco !== null ? '' : `${d.periodos[iDet].eje}: `;
  if (d.ap && d.ap.nombres[iDet]) {
    const A = acum(d, st, d.ap.filas, () => '·', miembro ? ruta.concat(st.sel) : ruta, d.periodos.length);
    const p = varPct(en(a, iDet, V), en(A.get('·'), iDet, V));
    ap = isFinite(p) ? `<small class="${p >= 0 ? 'verde' : 'rojo'}">${esc(pre)}${conSigno(p, pc(Math.abs(p)))} vs año pasado</small>` : `<small class="gris">${esc(pre)}nuevo vs año pasado</small>`;
  } else if (!d.ap) ap = '<small><button type="button" class="fi-link" data-acc="pedir-ap">Comparar con el año pasado</button></small>';
  else ap = '<small class="gris">sin año pasado</small>';
  let segunda;
  if (miembro || ruta.length) {
    const pD = en(base, iDet, V) ? en(a, iDet, V) / en(base, iDet, V) : NaN;
    const pA = iDet > 0 && en(base, iDet - 1, V) ? en(a, iDet - 1, V) / en(base, iDet - 1, V) : NaN;
    const dif = isFinite(pD) && isFinite(pA) ? `<small class="${pD >= pA ? 'verde' : 'rojo'}">${esc(d.periodos[iDet].eje)}: ${pp(pD - pA)}</small>` : '';
    segunda = `<div class="fi-cifra"><span>Peso en ${esc(enQue)}</span><b>${pc(vb ? v / vb : NaN)}</b>${dif}</div>`;
  } else {
    const p = pctCosto(sumT(a, T, C), sumT(a, T, B));
    segunda = `<div class="fi-cifra"><span>% costo · ${esc(cuando(d, x))}</span><b class="${nivelCosto(d, p).replace('c-alto', 'ambar').replace('c-roto', 'rojo')}">${pc(p)}</b><small class="gris">margen ${esc(fk(sumT(a, T, B) - sumT(a, T, C)))}</small></div>`;
  }
  h += `<div class="fi-cifras"><div class="fi-cifra"><span>Venta · ${esc(cuando(d, x))}</span><b>${esc(fk(v))}</b>${ap}</div>${segunda}</div>`;
  const sV = todos.map((i) => en(a, i, x.med));
  h += `<div class="fi-bloque"><div class="fi-tit">${unid(st) ? 'Unidades' : 'Venta'} por ${esc(per(d)[0])}<span>${esc(cUlt)}: ${esc(fmed(st, sV[kUlt]))}</span></div>${spark(sV, { barras: true, foco })}</div>`;
  if (miembro || ruta.length) {
    const sP = todos.map((i) => { const t = en(base, i, V); return t ? en(a, i, V) / t : NaN; });
    h += `<div class="fi-bloque"><div class="fi-tit">Peso en ${esc(enQue)}<span>${esc(cUlt)}: ${pc(sP[kUlt])}</span></div>${spark(sP, { foco })}</div>`;
  }
  const sC = todos.map((i) => pctCosto(en(a, i, C), en(a, i, B)));
  h += `<div class="fi-bloque"><div class="fi-tit">% costo<span>${esc(cUlt)}: ${pc(sC[kUlt])} · línea ${pc(d.umbrales[0], 0)}</span></div>${spark(sC, { foco, umbral: d.umbrales[0], color: 'var(--warning)' })}</div>`;
  const esProd = miembro && lvl === 2;
  if (esProd) {
    const sPr = todos.map((i) => (en(a, i, Q) > 0 ? en(a, i, V) / en(a, i, Q) : NaN));
    const sCa = todos.map((i) => (en(a, i, Q) > 0 ? en(a, i, NC) / en(a, i, Q) : NaN));
    h += `<div class="fi-bloque"><div class="fi-tit">Precio cobrado por unidad<span>${esc(cUlt)}: ${isFinite(sPr[kUlt]) ? 'S/ ' + sPr[kUlt].toFixed(2) : '—'}</span></div>${spark(sPr, { foco, color: 'var(--accent-deep)' })}
      <div class="fi-nota">Venta ÷ unidades, con impuestos y descuentos. Neto a precio de carta: ${isFinite(sCa[kUlt]) ? 'S/ ' + sCa[kUlt].toFixed(2) : '—'} por unidad.</div></div>`;
  }
  if (miembro && lvl < 2) {
    const hijos = acum(d, st, d.filas, (pi) => clave(d, st, pi, lvl + 1), ruta.concat(st.sel), d.periodos.length);
    const lista = [...hijos.entries()].map(([n, ar]) => [n, sumT(ar, T, V)]).filter((y) => y[1] > 0.5).sort((p, q) => q[1] - p[1]);
    const mx = lista.length ? lista[0][1] : 1;
    h += `<div class="fi-bloque"><div class="fi-tit">Lo que más vende<span>${lista.length} ${esc(niv[0][lvl + 1].toLowerCase())}</span></div>` +
      lista.slice(0, 6).map(([n, y]) => `<div class="fi-hijo"><span class="n" title="${esc(n)}">${esc(n)}</span><span class="b"><i style="width:${(100 * y / mx).toFixed(1)}%"></i></span><span class="p">${pc(v ? y / v : NaN, 0)}</span></div>`).join('') + '</div>';
  }
  const acc = [];
  if (miembro && lvl < 2) acc.push(`<button type="button" class="fi-btn" data-acc="bajar" data-id="${esc(st.sel)}">Abrir sus ${esc(niv[0][lvl + 1].toLowerCase())} ›</button>`);
  if (esProd) {
    const pi = d.filas.find((r) => enRuta(d, st, r[0], ruta) && d.prods[r[0]][2] === st.sel);
    const cod = pi ? d.codigos[pi[0]] : '';
    if (cod) acc.push(`<button type="button" class="fi-btn" data-acc="carta" data-id="${esc(cod)}">Ver en Costo de Carta ›</button>`);
  }
  if (miembro) acc.push('<button type="button" class="fi-btn sec" data-acc="soltar">Soltar</button>');
  if (acc.length) h += `<div class="fi-acc">${acc.join('')}</div>`;
  if (!miembro) h += '<div class="fi-nota">Tocá un nombre de la leyenda, una fila o un recuadro del Mapa para verlo acá.</div>';
  return h;
}

// ── Pestaña Resumen ──────────────────────────────────────────────────────
function tendencia(serie) {
  const ok = serie.filter((v) => isFinite(v));
  if (ok.length < 2) return '';
  const lo = Math.min(0, ...ok), hi = Math.max(...ok), n = serie.length;
  const px = (k) => 2 + (68 * k) / Math.max(1, n - 1), py = (v) => 16 - (14 * (v - lo)) / (hi - lo || 1);
  let dd = '';
  serie.forEach((v, k) => { if (isFinite(v)) dd += `${dd ? 'L' : 'M'}${px(k).toFixed(1)},${py(v).toFixed(1)}`; });
  return `<svg class="vm-tend" viewBox="0 0 72 18" aria-hidden="true"><path d="${dd}" fill="none" style="stroke:var(--accent)" stroke-width="1.5"/></svg>`;
}
function zonaResumen(d, st, x) {
  const { M, tot, orden, colorDe, lvl, todos, niv, foco } = x;
  const modo = st.celdas, med = x.med;
  const costo = modo === 'costo';
  const tT = sumT(tot, todos, med);
  const celda = (a, i) => {
    if (costo) { const p = pctCosto(en(a, i, C), en(a, i, B)); return { txt: pc(p), cls: nivelCosto(d, p), v: p }; }
    if (modo === 'pct') { const t = en(tot, i, med); const v = t ? en(a, i, med) / t : NaN; return { txt: v ? pc(v) : '—', v }; }
    const v = en(a, i, med); return { txt: Math.abs(v) < 0.5 ? '—' : (unid(st) ? fn(v) : fk(v).replace('S/ ', '')), v };
  };
  const calor = (v, mx) => (costo || !isFinite(v) || v <= 0 || mx <= 0 ? '' : `background-color: color-mix(in srgb, var(--accent) ${Math.round(4 + 30 * v / mx)}%, transparent)`);
  let h = `<div class="vm-tabla"><table><thead><tr><th>${esc(niv[0][lvl])}</th>`;
  todos.forEach((i) => {
    const p = d.periodos[i], marca = costo && p.igv;
    h += `<th class="${foco === i ? 'foco' : ''}"${marca ? ` title="${esc(p.igv)}"` : ''}>${esc(p.eje)}${p.parcial ? '*' : ''}${marca ? ' · IGV' : ''}</th>`;
  });
  h += `<th${costo ? ' title="El % de costo del rango entero"' : ''}>Total</th><th>Mix</th>${costo ? '' : `<th title="${esc(d.ayuda.costo)}">% costo</th><th title="${esc(d.ayuda.sin_desc)}">% sin desc.</th>`}<th>Tendencia</th></tr></thead><tbody>`;
  const fila = (n, a, cls, color) => {
    const cs = todos.map((i) => celda(a, i));
    const mx = Math.max(0, ...cs.map((c) => (isFinite(c.v) ? c.v : 0)));
    const t = sumT(a, todos, med), pcF = pctCosto(sumT(a, todos, C), sumT(a, todos, B));
    let r = `<tr class="${cls}"${cls.includes('f') ? ` data-acc="sel" data-id="${esc(n)}"` : ''}><td><span class="nomc">${color ? `<i style="background:${color}"></i>` : ''}<span title="${esc(n)}">${esc(n)}</span></span></td>`;
    cs.forEach((c, k) => { r += `<td class="${c.cls || ''}${foco === todos[k] ? ' foco' : ''}" style="${cls.includes('tot') ? '' : calor(c.v, mx)}">${c.txt}</td>`; });
    r += costo ? `<td class="${nivelCosto(d, pcF)}"><b>${pc(pcF)}</b></td>` : `<td><b>${esc(unid(st) ? fn(t) : fk(t).replace('S/ ', ''))}</b></td>`;
    r += `<td>${pc(tT ? t / tT : NaN)}</td>`;
    if (!costo) r += `<td class="${nivelCosto(d, pcF)}">${pc(pcF)}</td><td>${pc(pctCosto(sumT(a, todos, C), sumT(a, todos, NC)))}</td>`;
    r += `<td>${tendencia(cs.map((c) => c.v))}</td></tr>`;
    return r;
  };
  h += fila('Total', tot, 'tot', null);
  orden.forEach((n) => { h += fila(n, M.get(n), `f${st.sel === n ? ' sel' : ''}`, colorDe[n]); });
  h += '</tbody></table></div>';
  const sig = lvl < 2 ? `Tocá una fila para verla en la ficha; «›» en la leyenda baja a sus ${niv[0][lvl + 1].toLowerCase()}.` : 'Tocá una fila para verla en la ficha.';
  const cap = (costo ? `Costo ÷ venta neta (+ devolución del banco): en ámbar pasa del ${pc(d.umbrales[0], 0)} y en rojo del ${pc(d.umbrales[1], 0)}. ` : '') + sig + (todos.some((i) => d.periodos[i].parcial) ? ' * período incompleto.' : '');
  return [h, cap];
}

// ── Comparación: Qué movió y Mix y costo ─────────────────────────────────
function comparacion(raiz, keyFn) {
  const { data: d, st, x } = raiz.__d;
  const { ruta, iDet } = x, np = d.periodos.length;
  const A = acum(d, st, d.filas, keyFn, ruta, np);
  const a = new Map([...A.entries()].map(([k, ar]) => [k, enPer(ar, iDet)]));
  if (st.comp === 'ap') {
    if (!d.ap) return { pendiente: true };
    if (!d.ap.nombres[iDet]) return null;
    const R = acum(d, st, d.ap.filas, keyFn, ruta, np);
    return { a, b: new Map([...R.entries()].map(([k, ar]) => [k, enPer(ar, iDet)])), nombreA: d.periodos[iDet].largo, nombreB: d.ap.nombres[iDet], parejo: true };
  }
  if (iDet < 1) return null;
  return { a, b: new Map([...A.entries()].map(([k, ar]) => [k, enPer(ar, iDet - 1)])), nombreA: d.periodos[iDet].largo, nombreB: d.periodos[iDet - 1].largo,
    parejo: !d.periodos[iDet].parcial && !d.periodos[iDet - 1].parcial };
}
function sinComparar(raiz, cmp) {
  const { data: d, x } = raiz.__d;
  if (cmp && cmp.pendiente) { pedirAp(raiz); return ['<div class="vm-vacio">Trayendo el año pasado…</div>', '']; }
  return ['<div class="vm-vacio">No hay con qué comparar este período.</div>', `${cap1(d.periodos[x.iDet].largo)} es el primer período del rango o no tiene año pasado.`];
}
function zonaMovio(raiz) {
  const { data: d, st, x } = raiz.__d;
  const cmp = comparacion(raiz, (pi) => clave(d, st, pi, x.lvl));
  if (!cmp || cmp.pendiente) return sinComparar(raiz, cmp);
  const j = x.med, usaPP = st.cambio === 'Mix';
  let tA = 0, tB = 0;
  const nombres = new Set([...cmp.a.keys(), ...cmp.b.keys()]);
  for (const n of nombres) { tA += (cmp.a.get(n) || [])[j] || 0; tB += (cmp.b.get(n) || [])[j] || 0; }
  const filas = [...nombres].map((n) => { const va = (cmp.a.get(n) || [])[j] || 0, vb = (cmp.b.get(n) || [])[j] || 0; return { n, va, vb, d: va - vb, pp: (tA ? va / tA : 0) - (tB ? vb / tB : 0) }; })
    .filter((f) => Math.abs(f.va) + Math.abs(f.vb) > 0.5);
  const kk = usaPP ? 'pp' : 'd';
  filas.sort((p, q) => Math.abs(q[kk]) - Math.abs(p[kk]));
  const top = filas.slice(0, 10), resto = filas.slice(10);
  if (resto.length) top.push({ n: `Resto (${resto.length})`, resto: true, va: resto.reduce((s, f) => s + f.va, 0), vb: resto.reduce((s, f) => s + f.vb, 0), d: resto.reduce((s, f) => s + f.d, 0), pp: resto.reduce((s, f) => s + f.pp, 0) });
  const mx = Math.max(1e-9, ...top.map((f) => Math.abs(f[kk])));
  const fm = (v) => (unid(st) ? fn(Math.abs(v)) : fk(Math.abs(v)));
  const filasH = top.map((f) => {
    const w = (45 * Math.abs(f[kk])) / mx, pos = f[kk] >= 0;
    const bar = `<i class="${pos ? 'p' : 'm'}" style="${pos ? 'left:50%' : `left:${50 - w}%`};width:${w}%"></i>`;
    const txt = usaPP ? `${pp(f.pp)}<small>${pc(tA ? f.va / tA : NaN, 0)}</small>` : `${conSigno(f.d, fm(f.d))}<small>${f.vb > 0 ? conSigno(f.va / f.vb - 1, pc(Math.abs(f.va / f.vb - 1), 0)) : 'nuevo'}</small>`;
    return `<div class="mv-f${f.resto ? ' resto' : ''}"${f.resto ? '' : ` data-acc="sel" data-id="${esc(f.n)}"`} title="${esc(f.n)}: ${esc(fmed(st, f.vb))} → ${esc(fmed(st, f.va))}"><span class="n">${esc(f.n)}</span><span class="mv-bar">${bar}</span><span class="v">${txt}</span></div>`;
  }).join('');
  const P2 = comparacion(raiz, (pi) => d.prods[pi][2] + '\u0001' + d.prods[pi][1]);
  const prods = [...P2.a.entries()].map(([k, ar]) => ({ k, va: ar[j], vb: (P2.b.get(k) || [])[j] || 0 })).filter((y) => y.va > 0.5).sort((p, q) => q.va - p.va).slice(0, 12);
  const topH = prods.map((y, r) => {
    const [n, sub] = y.k.split('\u0001'), p = varPct(y.va, y.vb);
    return `<div class="top-f"><span class="r">${r + 1}</span><span class="n" title="${esc(n)}">${esc(n)}<small>${esc(sub)}</small></span><span class="v">${esc(fmed(st, y.va))}</span><span class="v ${isFinite(p) ? (p >= 0 ? 'verde' : 'rojo') : 'gris'}">${isFinite(p) ? conSigno(p, pc(Math.abs(p), 0)) : 'nuevo'}</span></div>`;
  }).join('');
  const eje = d.periodos[x.iDet].eje;
  const html = `<div class="mv"><div class="mv-caja"><div class="mv-tit">Qué movió ${esc(eje)}<span>${usaPP ? 'puntos del total' : (unid(st) ? 'unidades' : 'soles')}</span></div>${filasH}</div>
    <div class="mv-caja"><div class="mv-tit">Lo más vendido en ${esc(eje)}<span>vs ${st.comp === 'ap' ? 'año pasado' : 'anterior'}</span></div>${topH}</div></div>`;
  const dT = tA - tB;
  const res = `${conSigno(dT, unid(st) ? `${fn(Math.abs(dT))} und` : fk(Math.abs(dT)))}${tB ? ` (${conSigno(dT / tB, pc(Math.abs(dT / tB)))})` : ''}`;
  let cap = `${cap1(cmp.nombreA)} contra ${cmp.nombreB}: ${res}.`;
  if (!cmp.parejo) cap += ` Un período está incompleto en el rango: ${usaPP ? 'se compara el reparto, no el monto.' : 'el monto no se compara parejo; el mix sí.'}`;
  return [html, cap];
}

function zonaMix(raiz) {
  const { data: d, st, x } = raiz.__d;
  const cmp = comparacion(raiz, (pi) => `${clave(d, st, pi, x.lvl)}\u0001${d.prods[pi][2]}\u0001${d.prods[pi][1]}`);
  if (!cmp || cmp.pendiente) return sinComparar(raiz, cmp);
  // Antes = la comparación (b); después = el período en detalle (a). El
  // peso es la base del % de cada plato sobre la del período, sólo positiva.
  const keys = new Set([...cmp.a.keys(), ...cmp.b.keys()]);
  let BA = 0, BD = 0;
  for (const k of keys) { BA += Math.max(0, (cmp.b.get(k) || [])[B] || 0); BD += Math.max(0, (cmp.a.get(k) || [])[B] || 0); }
  const items = [];
  let pA = 0, pD = 0, mixT = 0, cosT = 0;
  for (const k of keys) {
    const an = cmp.b.get(k) || [], de = cmp.a.get(k) || [];
    const bA = Math.max(0, an[B] || 0), bD = Math.max(0, de[B] || 0);
    const wA = BA ? bA / BA : 0, wD = BD ? bD / BD : 0;
    let rA = bA > NETO_MIN ? (an[C] || 0) / bA : null, rD = bD > NETO_MIN ? (de[C] || 0) / bD : null;
    if (rA === null && rD === null) continue;
    if (rA === null) rA = rD;
    if (rD === null) rD = rA;
    // mezcla = (peso nuevo − peso antes) × costo antes; costo = peso nuevo × (costo nuevo − costo antes)
    const mix = (wD - wA) * rA, cos = wD * (rD - rA);
    pA += wA * rA; pD += wD * rD; mixT += mix; cosT += cos;
    const [miembro, prod, sub] = k.split('\u0001');
    items.push({ miembro, prod, sub, wA, wD, rA, rD, mix, cos, bA, bD });
  }
  const porM = new Map();
  for (const it of items) {
    const m = porM.get(it.miembro) || { n: it.miembro, mix: 0, cos: 0, bA: 0, bD: 0, cA: 0, cD: 0 };
    m.mix += it.mix; m.cos += it.cos; m.bA += it.bA; m.bD += it.bD; m.cA += it.rA * it.bA; m.cD += it.rD * it.bD;
    porM.set(it.miembro, m);
  }
  const miembros = [...porM.values()].sort((p, q) => Math.abs(q.mix + q.cos) - Math.abs(p.mix + p.cos));
  const dd = pD - pA, sube = (v) => (v >= 0 ? 'rojo' : 'verde');
  const frase = `<div class="mc-frase">El % de costo pasó de <b>${pc(pA)}</b> (${esc(cmp.nombreB)}) a <b>${pc(pD)}</b> (${esc(cmp.nombreA)}): <b class="${sube(dd)}">${pp(dd, 2)}</b>.
    De eso, <b class="${sube(mixT)}">${pp(mixT, 2)}</b> es por <span class="chip mix">lo que se vendió</span> —otra mezcla de platos— y <b class="${sube(cosT)}">${pp(cosT, 2)}</b> por <span class="chip cos">el costo de cada plato frente a su precio</span>.</div>`;
  const cuatro = `<div class="mc-cuatro">
    <div class="mc-c"><span>% costo · ${esc(cmp.nombreB)}</span><b>${pc(pA)}</b><small>punto de partida</small></div>
    <div class="mc-c"><span>Por la mezcla vendida</span><b class="${sube(mixT)}">${pp(mixT, 2)}</b><small>se vendió más de lo que cuesta más, o al revés</small></div>
    <div class="mc-c"><span>Por el costo de cada plato</span><b class="${sube(cosT)}">${pp(cosT, 2)}</b><small>receta, insumos, precio o descuentos</small></div>
    <div class="mc-c"><span>% costo · ${esc(cmp.nombreA)}</span><b>${pc(pD)}</b><small>${pp(dd, 2)} en total</small></div></div>`;
  const top = miembros.slice(0, 10);
  const mx = Math.max(1e-9, ...top.map((m) => Math.abs(m.mix + m.cos)));
  const barra = (v) => { const w = (45 * Math.abs(v)) / mx; return `<span class="mv-bar"><i class="${v >= 0 ? 'm' : 'p'}" style="${v >= 0 ? 'left:50%' : `left:${50 - w}%`};width:${w}%"></i></span>`; };
  const tablaM = top.map((m) => `<div class="mv-f" data-acc="sel" data-id="${esc(m.n)}" title="${esc(m.n)}: % costo ${pc(m.bA ? m.cA / m.bA : NaN)} → ${pc(m.bD ? m.cD / m.bD : NaN)}; peso ${pc(BA ? m.bA / BA : NaN)} → ${pc(BD ? m.bD / BD : NaN)}">
      <span class="n">${esc(m.n)}</span>${barra(m.mix + m.cos)}<span class="v">${pp(m.mix + m.cos, 2)}<small>mezcla ${pp(m.mix, 2)}</small></span></div>`).join('');
  const prods = items.filter((it) => Math.abs(it.mix + it.cos) > 0.00005).sort((p, q) => Math.abs(q.mix + q.cos) - Math.abs(p.mix + p.cos)).slice(0, 10);
  const tablaP = prods.map((it, r) => {
    const tag = Math.abs(it.mix) >= Math.abs(it.cos)
      ? `<span class="chip mix">${it.wD > it.wA ? 'más peso' : 'menos peso'} · cuesta ${pc(it.rA, 0)}</span>`
      : `<span class="chip cos">costo ${pc(it.rA, 0)} → ${pc(it.rD, 0)}</span>`;
    return `<div class="top-f ancho"><span class="r">${r + 1}</span><span class="n" title="${esc(it.prod)}">${esc(it.prod)}<small>${esc(it.sub)}</small></span><span>${tag}</span><span class="v ${sube(it.mix + it.cos)}">${pp(it.mix + it.cos, 2)}</span></div>`;
  }).join('');
  const html = `<div class="mc">${frase}${cuatro}<div class="mc-dos">
    <div class="mv-caja"><div class="mv-tit">Por ${esc(x.niv[1][x.lvl])}<span>pp del % de costo · rojo lo sube</span></div>${tablaM}</div>
    <div class="mv-caja"><div class="mv-tit">Los platos que más lo movieron<span>pp</span></div>${tablaP}</div></div>
    <div class="fuente">% costo = Σ peso × costo del plato, con peso = la base del % de cada plato sobre la del período. Mezcla = Σ (peso nuevo − peso antes) × costo antes; costo = Σ peso nuevo × (costo nuevo − costo antes): suman exacto el cambio. Un plato que antes no se vendió entra entero en la mezcla. Es la varianza de mezcla de ventas (Horngren, Datar y Rajan, <i>Cost Accounting</i>) llevada al % de costo; la elección de pesos es nuestra.</div></div>`;
  return [html, `${cap1(cmp.nombreA)} contra ${cmp.nombreB}, plato por plato dentro de ${x.ruta.length ? x.ruta[x.ruta.length - 1] : 'todo el local'}.`];
}

// ── Pestaña Mapa ─────────────────────────────────────────────────────────
function squarify(items, x0, y0, w, h) {
  const out = [], tot = items.reduce((s, a) => s + a.v, 0);
  if (tot <= 0 || w <= 1 || h <= 1) return out;
  let rest = items.map((a) => ({ ...a, a: (a.v * w * h) / tot }));
  const peor = (fila, lado) => { const s = fila.reduce((t, a) => t + a.a, 0); let mx = 0, mn = Infinity; for (const a of fila) { mx = Math.max(mx, a.a); mn = Math.min(mn, a.a); } return Math.max((lado * lado * mx) / (s * s), (s * s) / (lado * lado * mn)); };
  let x = x0, y = y0;
  while (rest.length) {
    const lado = Math.min(w, h), fila = [rest[0]];
    let i = 1;
    while (i < rest.length && peor(fila.concat(rest[i]), lado) <= peor(fila, lado)) { fila.push(rest[i]); i++; }
    const s = fila.reduce((t, a) => t + a.a, 0);
    if (w >= h) { const cw = s / h; let yy = y; for (const a of fila) { const hh = a.a / cw; out.push({ ...a, x, y: yy, w: cw, h: hh }); yy += hh; } x += cw; w -= cw; }
    else { const rh = s / w; let xx = x; for (const a of fila) { const ww = a.a / rh; out.push({ ...a, x: xx, y, w: ww, h: rh }); xx += ww; } y += rh; h -= rh; }
    rest = rest.slice(i);
  }
  return out;
}
function claseCosto(d, p) { if (!isFinite(p)) return 'tc0'; if (p > d.umbrales[1]) return 'tc5'; if (p > d.umbrales[0]) return 'tc4'; if (p > 0.35) return 'tc3'; if (p > 0.25) return 'tc2'; return 'tc1'; }
function zonaMapa(raiz, caja) {
  const { data: d, st, x } = raiz.__d;
  const { lvl, ruta, T, orden, colorDe, M, niv } = x;
  caja.innerHTML = `<div class="mapa"></div><div class="leyenda-mapa">${st.color === 'costo'
    ? '<span><i class="tc1"></i>hasta 25 %</span><span><i class="tc2"></i>25–35 %</span><span><i class="tc3"></i>35–45 %</span><span><i class="tc4"></i>45–70 %</span><span><i class="tc5"></i>más de 70 %</span><span><i class="tc0"></i>sin costo cargado</span>'
    : `<span>Cada color es un ${esc(niv[1][lvl])}, como en la barra.</span>`}</div>`;
  const el = caja.querySelector('.mapa');
  const W = el.clientWidth, H = el.clientHeight;
  const bloques = squarify(orden.map((n) => ({ n, v: Math.max(0, sumT(M.get(n), T, V)) })).filter((b) => b.v > 0), 0, 0, W, H);
  let html = '';
  for (const bl of bloques) {
    const cab = lvl < 2 && bl.h > 34 && bl.w > 60 ? 17 : 0;
    html += `<div class="bloq" style="left:${bl.x}px;top:${bl.y}px;width:${bl.w}px;height:${bl.h}px">${cab ? `<div class="bloq-cab">${esc(bl.n)}</div>` : ''}</div>`;
    let hijos;
    if (lvl < 2) {
      const Hm = acum(d, st, d.filas, (pi) => clave(d, st, pi, lvl + 1), ruta.concat(bl.n), d.periodos.length);
      hijos = [...Hm.entries()].map(([n, ar]) => ({ n, padre: bl.n, v: Math.max(0, sumT(ar, T, V)), c: sumT(ar, T, C), b: sumT(ar, T, B) })).filter((y) => y.v > 0).sort((p, q) => q.v - p.v);
    } else {
      const ar = M.get(bl.n);
      hijos = [{ n: bl.n, padre: '', v: bl.v, c: sumT(ar, T, C), b: sumT(ar, T, B) }];
    }
    for (const t of squarify(hijos, bl.x + 2, bl.y + cab + 2, bl.w - 4, bl.h - cab - 4)) {
      const p = pctCosto(t.c, t.b);
      const cls = st.color === 'costo' ? claseCosto(d, p) : '';
      const sty = st.color === 'costo' ? '' : `background:color-mix(in srgb, ${colorDe[t.padre || t.n] || 'var(--accent)'} ${t.padre ? 62 : 80}%, var(--bg-card));color:#fff;`;
      const txt = t.w > 58 && t.h > 28 ? `<b>${esc(t.n)}</b><span>${esc(fk(t.v))}${st.color === 'costo' && isFinite(p) ? ' · ' + pc(p, 0) : ''}</span>` : '';
      html += `<div class="tile ${cls}" style="${sty}left:${t.x}px;top:${t.y}px;width:${t.w}px;height:${t.h}px" data-acc="mapa" data-id="${esc(t.n)}" data-p="${esc(t.padre)}" data-tip="${esc(`<b>${esc(t.n)}</b>${t.padre ? esc(t.padre) + '<br>' : ''}${esc(fk(t.v))} · % costo ${pc(p)}`)}">${txt}</div>`;
    }
  }
  el.innerHTML = html;
  return `El tamaño es la venta de ${x.foco !== null ? d.periodos[x.foco].largo : `los ${T.length} ${per(d)[1]}`}. ${lvl < 2 ? `Cada bloque es un ${niv[1][lvl]} con sus ${niv[0][lvl + 1].toLowerCase()} adentro; tocá uno para abrirlo.` : 'Tocá un plato para verlo en la ficha.'}`;
}

// ── Pestaña Cálculo ──────────────────────────────────────────────────────
function pedidoLineas(d, st, x) {
  if (x.lvl !== 2 || st.sel === null) return null;
  const p = { l0: x.ruta[0], sub: x.ruta[1], prod: st.sel, eje: st.eje, claves: x.foco !== null ? [d.periodos[x.foco].clave] : [] };
  p.clave = JSON.stringify([p.l0, p.sub, p.prod, p.eje, p.claves, d.gran]);
  return p;
}
function zonaCalculo(raiz) {
  const { data: d, st, x } = raiz.__d;
  const ped = pedidoLineas(d, st, x);
  const quien = x.foco !== null ? d.periodos[x.foco].largo : `los ${x.T.length} ${per(d)[1]}`;
  if (ped) {
    if (!d.lineas || d.lineas.clave !== ped.clave) {
      if (raiz.__d.lineasPedidas !== ped.clave) { raiz.__d.lineasPedidas = ped.clave; raiz.__d.enviar('lineas', ped); }
      return [`<div class="vm-vacio">Trayendo las ventas de ${esc(st.sel)}…</div>`, ''];
    }
    const cols = ['Fecha', 'Cant.', 'Venta', 'IGV', 'Recargo', 'Descuento', 'Tipo de descuento', 'Devol. banco', 'Base', 'Costo', '% costo', '% sin desc.'];
    let h = `<div class="vm-tabla"><table><thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>`;
    d.lineas.filas.forEach((f, k) => {
      h += `<tr class="${k === 0 ? 'tot' : ''}">` + f.map((v, i) => {
        if (i === 0 || i === 6) return `<td class="izq">${esc(v ?? '')}</td>`;
        if (i === 1) return `<td>${v == null ? '—' : fn(v)}</td>`;
        if (i >= 10) return `<td class="${i === 10 ? nivelCosto(d, v ?? NaN) : ''}">${pc(v ?? NaN)}</td>`;
        return `<td>${v == null ? '—' : fs(v)}</td>`;
      }).join('') + '</tr>';
    });
    h += '</tbody></table></div>';
    const n = d.lineas.n, mostradas = Math.max(0, d.lineas.filas.length - 1);
    return [h, `Cada venta de ${st.sel} · ${quien}${n > mostradas ? ` · las ${mostradas} más nuevas de ${fn(n)} (el total las cuenta a todas)` : ''}. Base = Venta − IGV − Recargo + devolución del banco. «Soltar» en la ficha vuelve a la lista.`];
  }
  const Mp = acum(d, st, d.filas, (pi) => `${clave(d, st, pi, 0)}\u0001${d.prods[pi][1]}\u0001${d.prods[pi][2]}`, x.ruta, d.periodos.length);
  const q = sinTilde(st.calc);
  const lin = (a) => { const s = (j) => sumT(a, x.T, j); return { q: s(Q), v: s(V), igv: s(IGV), rec: s(REC), desc: s(DESC), dev: s(DEV), b: s(B), c: s(C), nc: s(NC), sc: s(SC) }; };
  const todas = [...Mp.entries()].map(([k, a]) => { const [l0, sub, n] = k.split('\u0001'); return { l0, sub, n, ...lin(a) }; })
    .filter((f) => Math.abs(f.v) > 0.005 || Math.abs(f.c) > 0.005);
  const filas = todas.filter((f) => !q || sinTilde(f.n).includes(q)).sort((p, r) => r.v - p.v);
  const tot = filas.reduce((t, f) => { for (const k of ['q', 'v', 'igv', 'rec', 'desc', 'dev', 'b', 'c', 'nc', 'sc']) t[k] += f[k]; return t; }, { q: 0, v: 0, igv: 0, rec: 0, desc: 0, dev: 0, b: 0, c: 0, nc: 0, sc: 0 });
  const fila = (f, cls, attrs) => { const p = pctCosto(f.c, f.b);
    return `<tr class="${cls}"${attrs}><td><span class="nomc"><span title="${esc(f.n)}${f.sub ? ' · ' + esc(f.sub) : ''}">${esc(f.n)}</span></span></td><td>${fn(f.q)}</td><td>${fs(f.v)}</td><td>${fs(f.igv)}</td><td>${fs(f.rec)}</td><td>${fs(f.desc)}</td><td>${fs(f.dev)}</td><td>${fs(f.b)}</td><td>${fs(f.c)}</td><td class="${nivelCosto(d, p)}">${pc(p)}</td><td>${pc(pctCosto(f.c, f.nc))}</td><td>${f.sc > 0.005 ? `<span class="ambar">${fs(f.sc)}</span>` : '—'}</td></tr>`; };
  let h = `<div class="calc-cab"><input class="vm-buscar" data-acc="calc" value="${esc(st.calc)}" placeholder="Filtrar productos…" aria-label="Filtrar productos"><span class="gris" style="font-size:12px">${filas.length} productos</span></div>`;
  h += '<div class="vm-tabla"><table><thead><tr><th>Producto</th><th>Cant.</th><th>Venta</th><th>IGV</th><th>Recargo</th><th>Descuento</th><th>Devol. banco</th>' +
    `<th title="Venta − IGV − Recargo + lo que devuelve el banco. Cero si se vendió sin costo cargado: no entra en el %.">Base</th><th>Costo</th><th title="${esc(d.ayuda.costo)}">% costo</th><th title="${esc(d.ayuda.sin_desc)}">% sin desc.</th><th title="Venta sin costo cargado en el POS: no entra en el %">Sin costo</th></tr></thead><tbody>`;
  h += fila({ n: 'Total', sub: '', ...tot }, 'tot', '');
  filas.slice(0, 300).forEach((f) => { h += fila(f, 'f', ` data-acc="prod" data-id="${esc(JSON.stringify([f.l0, f.sub, f.n]))}"`); });
  h += '</tbody></table></div>';
  return [h, `Un producto por fila · ${quien}. Tocá uno para ver sus ventas una por una. Base = Venta − IGV − Recargo + devolución del banco.`];
}

// ── Año pasado ───────────────────────────────────────────────────────────
function pedirAp(raiz) {
  if (raiz.__d.apPedido) return;
  raiz.__d.apPedido = true;
  raiz.__d.enviar('ap', { n: Date.now() });
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.vm-cuerpo')) {
    raiz.innerHTML = `<div class="vm-kpis" data-zona="kpis"></div><div class="vm-ctrl" data-zona="ctrl"></div>
      <div class="vm-cuerpo"><div class="vm-caja vm-graf"><div class="vm-ruta" data-zona="ruta"></div><div class="vm-gfila"><div class="vm-svg" data-zona="svg"></div><div class="vm-ley" data-zona="ley"></div></div></div>
      <aside class="vm-caja vm-ficha" data-zona="ficha" aria-label="Ficha"></aside></div>
      <div class="vm-pie" data-zona="pie"></div><div class="vm-zona" data-zona="zona"></div>
      <datalist id="vm-prods"></datalist><div class="vm-tip" data-zona="tip"></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  const x = calcular(raiz);
  z('kpis').innerHTML = htmlKpis(d, st, x);
  const buscando = raiz.querySelector('.vm-buscar[data-acc="buscar"]');
  if (!buscando || raiz.__d.ctrlFirma !== `${d.gran}|${st.eje}|${st.medida}|${st.escala}|${d.hay_area}`) {
    z('ctrl').innerHTML = htmlControles(d, st);
    raiz.__d.ctrlFirma = `${d.gran}|${st.eje}|${st.medida}|${st.escala}|${d.hay_area}`;
  }
  z('ruta').innerHTML = htmlRuta(d, st, x);
  z('ley').innerHTML = htmlLeyenda(d, st, x);
  const svg = z('svg');
  svg.innerHTML = htmlGrafico(d, st, x, Math.max(240, svg.clientWidth || 600), Math.max(150, svg.clientHeight || 240));
  z('ficha').innerHTML = htmlFicha(d, st, x);
  z('pie').innerHTML = htmlPie(d, st, x);
  dibujarZona(raiz);
}
function dibujarZona(raiz) {
  const { data: d, st, x } = raiz.__d;
  const caja = raiz.querySelector('[data-zona="zona"]'), cap = raiz.querySelector('[data-zona="cap"]');
  const y = caja.querySelector('.vm-tabla')?.scrollTop || 0;
  let html = '', texto = '';
  if (st.zona === 'Mapa') { texto = zonaMapa(raiz, caja); cap.textContent = texto + (d.nota ? ` ${d.nota}` : ''); return; }
  if (st.zona === 'Movio') [html, texto] = zonaMovio(raiz);
  else if (st.zona === 'Mix') [html, texto] = zonaMix(raiz);
  else if (st.zona === 'Calculo') [html, texto] = zonaCalculo(raiz);
  else [html, texto] = zonaResumen(d, st, x);
  caja.innerHTML = html;
  cap.textContent = texto + (d.nota ? ` ${d.nota}` : '');
  const t = caja.querySelector('.vm-tabla');
  if (t && raiz.__d.mismaZona) t.scrollTop = y;
}
function recordar(st) {
  guardar(CLAVE, { eje: st.eje, medida: st.medida, escala: st.escala, zona: st.zona, celdas: st.celdas, cambio: st.cambio, comp: st.comp, color: st.color, ruta: st.ruta });
}
function llenarBuscador(raiz) {
  const d = raiz.__d.data, st = raiz.__d.st, tot = new Map();
  for (const r of d.filas) tot.set(r[0], (tot.get(r[0]) || 0) + r[2 + V]);
  const ids = [...tot.keys()].filter((pi) => tot.get(pi) > 0.5).sort((a, b) => tot.get(b) - tot.get(a));
  raiz.__d.buscar = new Map(ids.map((pi) => [`${d.prods[pi][2]} · ${d.prods[pi][1]}`, pi]));
  raiz.querySelector('#vm-prods').innerHTML = [...raiz.__d.buscar.keys()].map((k) => `<option value="${esc(k)}"></option>`).join('');
  void st;
}

function enlazar(raiz) {
  const tip = () => raiz.querySelector('[data-zona="tip"]');
  const mostrarTip = (ev, html) => {
    const t = tip(); if (!t) return;
    t.innerHTML = html; t.style.display = 'block';
    const r = raiz.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight;
    let left = ev.clientX - r.left + 14, top = ev.clientY - r.top + 14;
    if (left + w > r.width - 4) left = ev.clientX - r.left - w - 14;
    if (ev.clientY + 14 + h > window.innerHeight - 4) top = ev.clientY - r.top - h - 14;
    t.style.left = `${Math.max(0, left)}px`; t.style.top = `${Math.max(0, top)}px`;
  };
  const ocultarTip = () => { const t = tip(); if (t) t.style.display = 'none'; };
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    const st = raiz.__d.st, d = raiz.__d.data;
    raiz.__d.mismaZona = false;
    if (!b || !raiz.contains(b)) {
      const col = ev.target.closest('.g-col');
      if (col) {
        const i = +col.dataset.i, k = d.periodos[i].clave;
        st.foco = st.foco === k ? null : k;
        if (st.foco !== null && d.periodos[i].parcial && st.comp === 'ant') st.cambio = 'Mix';
        ocultarTip(); dibujar(raiz);
      }
      return;
    }
    if (b.tagName === 'INPUT') return;
    const acc = b.dataset.acc, id = b.dataset.id;
    ev.stopPropagation();
    if (acc === 'bajar') { st.ruta = st.ruta.concat(id); st.sel = null; }
    else if (acc === 'sel') { st.sel = st.sel === id ? null : id; raiz.__d.mismaZona = true; }
    else if (acc === 'subir') { st.ruta = st.ruta.slice(0, +id); st.sel = null; }
    else if (acc === 'soltar') st.sel = null;
    else if (acc === 'mapa') { ocultarTip(); if (b.dataset.p) { st.ruta = st.ruta.concat(b.dataset.p); } st.sel = id; }
    else if (acc === 'prod') { const [l0, sub, n] = JSON.parse(id); st.ruta = [l0, sub]; st.sel = n; }
    else if (acc === 'carta') { raiz.__d.enviar('carta', { cod: id, n: Date.now() }); return; }
    else if (acc === 'pedir-ap') { pedirAp(raiz); return; }
    else if (acc === 'gran') { if (id !== d.gran) { st.foco = null; raiz.__d.enviar('gran', id); } return; }
    else if (acc === 'comp') { st.comp = id; if (id === 'ap' && !d.ap) pedirAp(raiz); }
    else if (['eje', 'medida', 'escala', 'zona', 'celdas', 'cambio', 'color'].includes(acc)) {
      if (acc === 'eje' && id !== st.eje) { st.ruta = []; st.sel = null; }
      st[acc] = id;
    } else return;
    recordar(st);
    dibujar(raiz);
  });
  raiz.addEventListener('change', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    const pi = raiz.__d.buscar && raiz.__d.buscar.get(ev.target.value);
    if (pi === undefined) return;
    const { data: d, st } = raiz.__d;
    st.ruta = [clave(d, st, pi, 0), d.prods[pi][1]]; st.sel = d.prods[pi][2];
    ev.target.value = '';
    recordar(st); dibujar(raiz);
  });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'calc') return;
    const st = raiz.__d.st, pos = ev.target.selectionStart;
    st.calc = ev.target.value;
    raiz.__d.mismaZona = false;
    dibujarZona(raiz);
    const i2 = raiz.querySelector('.vm-buscar[data-acc="calc"]');
    if (i2) { i2.focus(); i2.setSelectionRange(pos, pos); }
  });
  raiz.addEventListener('mousemove', (ev) => {
    const tile = ev.target.closest('.tile');
    if (tile) { mostrarTip(ev, tile.dataset.tip); return; }
    const col = ev.target.closest('.g-col');
    if (!col) { ocultarTip(); return; }
    const { data: d, st, x } = raiz.__d;
    const i = +col.dataset.i, t = en(x.tot, i, x.med), r = ev.target.closest('rect.t');
    if (r) {
      const tr = x.tr[+r.dataset.t], v = tr.miembros.reduce((s, m) => s + en(x.M.get(m), i, x.med), 0);
      mostrarTip(ev, `<b>${esc(tr.nombre)}</b>${esc(d.periodos[i].largo)}<br>${esc(fmed(st, v))} · ${pc(t ? v / t : NaN)} del período`);
    } else mostrarTip(ev, `<b>${esc(d.periodos[i].largo)}</b>${esc(fmed(st, t))}`);
  });
  raiz.addEventListener('mouseleave', ocultarTip);
  // Otro ancho, otra barra y otro mapa (se dibujan al ancho de su caja).
  let espera = null;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => { if (raiz.isConnected) dibujar(raiz); }, 150); });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.periodos || !data.periodos.length || !data.filas) return;
  let raiz = parentElement.querySelector('.vm');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'vm';
    parentElement.appendChild(raiz);
    raiz.__d = {
      st: Object.assign({ eje: 'Carta', medida: 'Soles', escala: 'Monto', zona: 'Resumen', celdas: 'Venta', cambio: 'Monto', comp: 'ant', color: 'costo', ruta: [] },
        leer(CLAVE, {}), { foco: null, sel: null, calc: '' }),
    };
    if (!Array.isArray(raiz.__d.st.ruta)) raiz.__d.st.ruta = [];
    enlazar(raiz);
  }
  const prev = raiz.__d.data;
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.data = data;
  if (data.ap) raiz.__d.apPedido = true;
  if (!prev || prev.filas !== data.filas) { raiz.__d.ctrlFirma = null; }
  dibujar(raiz);
  llenarBuscador(raiz);
}
