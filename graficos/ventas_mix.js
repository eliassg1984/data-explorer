// Ventas › «Mix de carta» (reglas #702 y #763).
//
// La monta graficos/ventas_mix.py::_ventas_mix con st.components.v2 (sin
// iframe, estilos en un shadow root). Desde la #763 no se aprieta: cuatro
// indicadores eligen qué se mide, una sola zona grande por pestaña (Gráfico,
// Tabla, Qué movió, Mapa, Mix y costo, Cálculo) y, al costado, la lista con
// la ficha de lo elegido. Python manda las sumas por producto y período; todo
// lo demás se resuelve acá sin una corrida. Vuelven a Python: `gran` (otra
// granularidad), `ap` (el año pasado, pedido DESPUÉS de dibujar: la tarjeta no
// lo espera), `lineas` (Cálculo de un producto, venta por venta) y `carta` (el
// salto a Costo de Carta).
//
// LAS CUENTAS SON LAS DE ventas_mix.py: `pctCosto` es `pct_costo` (costo ÷
// base, sin cociente donde no hay costo o la base no llega a medio sol),
// `tramos` es `tramos` (siete con su tono y «Resto (N)», nunca «Resto (1)»),
// y el Cálculo suma lo mismo que `calculo`. El test busca las fórmulas
// escritas igual.
//
// Python manda en `data`: `gran`, `grans`, `periodos` ([{clave, eje,
// largo, parcial, igv}]), `prods` ([grupo, subgrupo, nombre, área]),
// `codigos` (uno por producto, para Costo de Carta), `filas` ([producto,
// período, V, Q, C, B, NC, SC, IGV, REC, DESC, DEV]), `ap` (null o {filas,
// nombres}: la misma forma, con el período de ESTE rango con el que se
// compara cada fila), `lineas`, `nota`, `hay_area`, `niveles`, `umbrales`
// ([0.45, 0.70]), `tramos` (7), `ayuda` y `alcance` (el filtro «Venta»).
//
// EL FILTRO «VENTA» (regla #755, `ventas_alcance.js`, antepuesto por
// Python): qué grupos y subgrupos se cuentan en ESTA tarjeta. Abre en Carta
// + Eventos y no se recuerda entre sesiones. Recorta `filas` y `ap.filas`
// por producto ANTES de todo lo demás (`conAlcance`): las cuentas de abajo
// no se enteran.

const CLAVE = 'vt_mix_est2';
const V = 0, Q = 1, C = 2, B = 3, NC = 4, SC = 5, IGV = 6, REC = 7, DESC = 8, DEV = 9;
const NM = 10;
const TONO = (k) => `var(--vm-t${k % 7})`;
const RESTO = 'var(--vm-apagado)';
const NETO_MIN = 0.5;
const SEP = '|~|';
const KPIS = [['venta', 'Venta'], ['costo', '% de costo'], ['margen', 'Margen bruto'], ['und', 'Unidades']];
const NOM_KPI = Object.fromEntries(KPIS);
const ZONAS = [['Graf', 'Gráfico'], ['Tabla', 'Tabla'], ['Movio', 'Qué movió'], ['Mapa', 'Mapa'], ['Mix', 'Mix y costo'], ['Calculo', 'Cálculo']];

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
  // `tramos`: `max` con tono y el resto junto; con `max` + 1, todos.
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
const ordenDe = (k) => (k === 'costo' ? 'venta' : k);
function valor(a, T, k) {
  // Lo que mide cada indicador. Un % no se suma: sale de sus dos sumas.
  if (k === 'und') return sumT(a, T, Q);
  if (k === 'margen') return sumT(a, T, B) - sumT(a, T, C);
  if (k === 'costo') return pctCosto(sumT(a, T, C), sumT(a, T, B));
  return sumT(a, T, V);
}
const fmedK = (k, v) => (!isFinite(v) ? '—' : k === 'und' ? `${fn(v)} und` : k === 'costo' ? pc(v) : fk(v));
const deFila = (ar, k) => (k === 'und' ? ar[Q] : k === 'margen' ? ar[B] - ar[C] : ar[V]);

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
  const k = st.kpi, ko = ordenDe(k);
  const llave = (pi) => clave(d, st, pi, lvl);
  const M = acum(d, st, d.filas, llave, ruta, np);
  const MA = d.ap ? acum(d, st, d.ap.filas, llave, ruta, np) : new Map();
  const tot = total(M, np), totA = total(MA, np);
  const totLocal = total(acum(d, st, d.filas, () => '·', [], np), np);
  let foco = d.periodos.findIndex((p) => p.clave === st.foco);
  if (foco < 0) { foco = null; st.foco = null; }
  const T = foco !== null ? [foco] : todos;
  // Se compara sólo lo que tiene año pasado: sin base no es cero (#660).
  const TC = d.ap ? T.filter((i) => d.ap.nombres[i]) : [];
  const orden = [...M.keys()].filter((n) => todos.some((i) => Math.abs(en(M.get(n), i, V)) > 0.5 || Math.abs(en(M.get(n), i, Q)) > 0.01))
    .sort((a, b) => valor(M.get(b), todos, ko) - valor(M.get(a), todos, ko));
  let ci = 0;
  const tr = tramos(orden, d.tramos).map(([nombre, miembros, resto]) => ({ nombre, miembros, resto, color: resto ? RESTO : TONO(ci++) }));
  const colorDe = {};
  tr.forEach((t) => t.miembros.forEach((m) => { colorDe[m] = t.color; }));
  const completos = todos.filter((i) => !d.periodos[i].parcial);
  const iDet = foco !== null ? foco : (completos.length ? completos[completos.length - 1] : np - 1);
  if (st.sel !== null && !M.has(st.sel)) st.sel = null;
  raiz.__d.x = { np, todos, niv, ruta, lvl, k, ko, M, MA, tot, totA, totLocal, foco, T, TC, orden, tr, colorDe, iDet, arbol: null };
  return raiz.__d.x;
}
const per = (d) => ({ 'Día': ['día', 'días'], Semana: ['semana', 'semanas'], Mes: ['mes', 'meses'], 'Año': ['año', 'años'] }[d.gran] || ['período', 'períodos']);
const unid = (st) => st.kpi === 'und';
function cuando(d, x) { return x.foco !== null ? d.periodos[x.foco].eje : `${x.T.length} ${x.T.length === 1 ? per(d)[0] : per(d)[1]}`; }

// ── Indicadores ──────────────────────────────────────────────────────────
function curva(serie) {
  const xs = serie.map((v) => (isFinite(v) ? v : 0)), mn = Math.min(...xs), mx = Math.max(...xs), r = mx - mn || 1, n = Math.max(1, xs.length - 1);
  return xs.map((v, i) => `${i ? 'L' : 'M'}${(i * 100 / n).toFixed(1)},${(31 - (v - mn) / r * 28).toFixed(1)}`).join('');
}
function variacion(d, x, a, aA, k) {
  // Contra el año pasado: el % de costo en puntos y al revés (subir es malo).
  if (!d.ap) return { txt: '…', cls: 'gris', nota: 'trayendo el año pasado' };
  if (!x.TC.length) return { txt: '', cls: 'gris', nota: 'sin año pasado' };
  const h = valor(a, x.TC, k), b = valor(aA, x.TC, k);
  const nota = `vs año pasado${x.TC.length < x.T.length ? ` · ${x.TC.length} de ${x.T.length}` : ''}`;
  if (k === 'costo') {
    if (!isFinite(h) || !isFinite(b)) return { txt: '—', cls: 'gris', nota };
    return { txt: `${h > b ? '▲' : '▼'} ${Math.abs((h - b) * 100).toFixed(1)} pp`, cls: h > b ? 'rojo' : 'verde', nota };
  }
  const p = varPct(h, b);
  if (!isFinite(p)) return { txt: '—', cls: 'gris', nota };
  return { txt: `${p > 0 ? '▲' : '▼'} ${Math.abs(p * 100).toFixed(1)}%`, cls: p > 0 ? 'verde' : 'rojo', nota };
}
function htmlKpis(d, st, x) {
  const { tot, totA, T, todos } = x;
  return KPIS.map(([k, nom]) => {
    const v = valor(tot, T, k), ve = variacion(d, x, tot, totA, k);
    const clase = k === 'costo' ? nivelCosto(d, v).replace('c-alto', 'ambar').replace('c-roto', 'rojo') : '';
    return `<button type="button" class="vm-kpi${st.kpi === k ? ' on' : ''}" data-acc="kpi" data-id="${k}" aria-pressed="${st.kpi === k}"${k === 'costo' ? ` title="${esc(d.ayuda.costo)}"` : ''}>
      <svg class="vm-kpi-c" viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><path d="${curva(todos.map((i) => valor(tot, [i], k)))}"/></svg>
      <span class="vm-kpi-rot">${esc(nom)}${k === 'costo' ? '' : ` · ${esc(cuando(d, x))}`}</span>
      <span class="vm-kpi-val ${clase}">${esc(k === 'und' ? fn(v) : fmedK(k, v))}</span>
      <span class="vm-kpi-var"><span class="${ve.cls}">${esc(ve.txt)}</span> ${esc(ve.nota)}</span></button>`;
  }).join('');
}
function htmlOjo(d, st, x) {
  const sc = sumT(x.totLocal, x.T, SC);
  if (sc <= 0.5) return '';
  const sin = new Map();
  for (const r of d.filas) if (x.T.includes(r[1]) && r[2 + SC] > 0.5) sin.set(d.prods[r[0]][2], (sin.get(d.prods[r[0]][2]) || 0) + r[2 + SC]);
  const lista = [...sin.entries()].sort((a, b) => b[1] - a[1]);
  return `<button type="button" class="vm-ojo" data-acc="ojo" title="${esc('Vendido sin costo en el POS: no entra en ningún % de costo. ' + lista.slice(0, 6).map(([n, s]) => `${n} S/ ${fn(s)}`).join('; '))}">Sin costo cargado: ${esc(fk(sc))} · ${lista.length} prod.</button>`;
}

// ── Controles ────────────────────────────────────────────────────────────
function seg(opciones, actual, acc, apagadas = {}) {
  if (!opciones.length) return '';
  return `<div class="vm-seg" role="group">${opciones.map(([val, rot]) => `<button type="button" data-acc="${acc}" data-id="${esc(val)}" class="${val === actual ? 'on' : ''}" ${apagadas[val] ? `disabled title="${esc(apagadas[val])}"` : ''}>${esc(rot)}</button>`).join('')}</div>`;
}
function menu(acc, rot, opciones, actual) {
  return `<select class="vm-men" data-acc="${acc}" aria-label="${esc(rot)}">${opciones.map(([v, t, off]) => `<option value="${esc(v)}"${v === actual ? ' selected' : ''}${off ? ' disabled' : ''}>${esc(rot)}: ${esc(t)}</option>`).join('')}</select>`;
}
function htmlPie(d, st) {
  const ejes = d.hay_area ? [['Carta', 'Carta'], ['Área', 'Área']] : [['Carta', 'Carta']];
  const medida = st.kpi === 'und' ? 'und' : st.kpi === 'costo' ? 'pct' : 'soles';
  return seg(ZONAS, st.zona, 'zona') + '<span class="vm-esp"></span>' +
    menu('eje', 'Abrir por', ejes, st.eje) +
    menu('medir', 'Medir', [['soles', 'Soles'], ['und', 'Unidades'], ['pct', '% de costo', true]], medida) +
    menu('gran', 'Agrupar', d.grans.map((g) => [g, g]), d.gran);
}
function apDisponible(d, i) { return !d.ap || !!d.ap.nombres[i]; }

// ── La lista y la ficha ──────────────────────────────────────────────────
function htmlRuta(d, st, x) {
  const todo = x.niv[2];
  const partes = [x.ruta.length ? `<button type="button" data-acc="subir" data-id="0">${esc(todo)}</button>` : `<b>${esc(todo)}</b>`];
  x.ruta.forEach((n, k) => { partes.push('<span class="sep">›</span>'); partes.push(k === x.ruta.length - 1 ? `<b>${esc(n)}</b>` : `<button type="button" data-acc="subir" data-id="${k + 1}">${esc(n)}</button>`); });
  return partes.join(' ');
}
function htmlLista(d, st, x) {
  const { orden, M, T, tot, lvl, niv, colorDe, k, ko, ruta } = x;
  const tT = valor(tot, T, ko), de = ruta.length ? `de ${ruta[ruta.length - 1]}` : 'del total';
  return orden.map((n) => {
    const a = M.get(n), v = valor(a, T, k), parte = pc(tT ? valor(a, T, ko) / tT : NaN, 0);
    const sub = k === 'costo' ? `pesa ${parte}` : `${parte} ${de} · costo ${pc(pctCosto(sumT(a, T, C), sumT(a, T, B)), 0)}`;
    const on = st.sel === n && !st.fiT;
    return `<div class="vm-li${on ? ' sel' : ''}"><button type="button" class="vm-lib" data-acc="sel" data-id="${esc(n)}" aria-pressed="${on}"><span class="nom" title="${esc(n)}"><i style="background:${colorDe[n]}"></i>${esc(n)}</span><b>${esc(fmedK(k, v))}</b><small>${esc(sub)}</small></button>${lvl < 2 ? `<button type="button" class="vm-bajar" data-acc="bajar" data-id="${esc(n)}" title="Ver sus ${esc(niv[0][lvl + 1].toLowerCase())}" aria-label="Ver sus ${esc(niv[0][lvl + 1].toLowerCase())}">›</button>` : ''}</div>`;
  }).join('');
}
function filaFicha(rot, val, cls = '', tip = '') { return `<div class="fi-f${cls === 'ambar' ? ' ad' : ''}"${tip ? ` title="${esc(tip)}"` : ''}><span>${esc(rot)}</span><b class="${cls}">${esc(val)}</b></div>`; }
function codigoDe(d, st, ruta, nombre) {
  const r = d.filas.find((f) => enRuta(d, st, f[0], ruta) && d.prods[f[0]][2] === nombre);
  return r ? d.codigos[r[0]] : '';
}
function fichaDe(d, st, x, tit, a, aA, padre, nomPadre, ruta, esProd, botones) {
  const { T, TC, totLocal } = x;
  const v = sumT(a, T, V), vC = sumT(a, TC, V), vA = sumT(aA, TC, V), p = varPct(vC, vA);
  const cst = pctCosto(sumT(a, T, C), sumT(a, T, B)), gT = sumT(totLocal, T, V);
  let h = `<h3 title="${esc(tit)}">${esc(tit)}</h3>`;
  h += filaFicha('Venta', fk(v) + (d.ap && TC.length && isFinite(p) ? `  ${conSigno(p, pc(Math.abs(p), 0))}` : ''));
  h += filaFicha(`Pesa en ${nomPadre}`, pc(sumT(padre, T, V) ? v / sumT(padre, T, V) : NaN));
  if (nomPadre !== 'el total') h += filaFicha('Pesa en el total', pc(gT ? v / gT : NaN));
  h += filaFicha('% costo', pc(cst), nivelCosto(d, cst).replace('c-alto', 'ambar').replace('c-roto', 'rojo'), d.ayuda.costo);
  h += filaFicha('Margen bruto', fk(sumT(a, T, B) - sumT(a, T, C)));
  const q = sumT(a, T, Q);
  h += filaFicha('Unidades', fn(q));
  if (esProd && q > 0) h += filaFicha('Precio cobrado por unidad', `S/ ${(v / q).toFixed(2)}`, '', 'Venta ÷ unidades, con impuestos y descuentos');
  const acc = [...botones];
  if (esProd) { const cod = codigoDe(d, st, ruta, tit); if (cod) acc.unshift(`<button type="button" class="fi-btn" data-acc="carta" data-id="${esc(cod)}">Ver en Costo de Carta ›</button>`); }
  if (acc.length) h += `<div class="fi-acc">${acc.join('')}</div>`;
  return h;
}
function htmlFicha(d, st, x) {
  const { M, MA, tot, totLocal, T, lvl, ruta, niv } = x;
  const soltar = '<button type="button" class="fi-btn sec" data-acc="soltar">Soltar</button>';
  if (st.fiT && st.zona === 'Tabla') {
    const A = arbol(d, st, x), partes = st.fiT.split(SEP), n = partes.length - 1, a = A.niveles[n] && A.niveles[n].get(st.fiT);
    if (a) {
      const padre = n > 0 ? A.niveles[n - 1].get(partes.slice(0, -1).join(SEP)) : tot;
      const nomP = n > 0 ? partes[n - 1] : (ruta.length ? ruta[ruta.length - 1] : 'el total');
      const aA = acum(d, st, d.ap ? d.ap.filas : [], A.llaveDe(n), ruta, x.np).get(st.fiT);
      return fichaDe(d, st, x, partes[n], a, aA, padre, nomP, ruta.concat(partes.slice(0, -1)), lvl + n === 2, [soltar]);
    }
  }
  if (st.sel !== null) {
    const botones = lvl < 2 ? [`<button type="button" class="fi-btn" data-acc="bajar" data-id="${esc(st.sel)}">Abrir sus ${esc(niv[0][lvl + 1].toLowerCase())} ›</button>`, soltar] : [soltar];
    return fichaDe(d, st, x, st.sel, M.get(st.sel), MA.get(st.sel), tot, ruta.length ? ruta[ruta.length - 1] : 'el total', ruta, lvl === 2, botones);
  }
  const nombre = ruta.length ? ruta[ruta.length - 1] : (d.alcanceRot || 'Toda la carta');
  const comp = x.todos.filter((i) => !d.periodos[i].parcial);
  const prods = new Set();
  for (const r of d.filas) if (T.includes(r[1]) && r[2 + V] > 0.5 && enRuta(d, st, r[0], ruta)) prods.add(d.prods[r[0]][1] + '\u0001' + d.prods[r[0]][2]);
  const gT = sumT(totLocal, T, V), v = sumT(tot, T, V), sc = sumT(tot, T, SC);
  let h = `<h3 title="${esc(nombre)}">${esc(nombre)} · ${esc(cuando(d, x))}</h3>`;
  if (ruta.length) h += filaFicha('Pesa en el total', pc(gT ? v / gT : NaN));
  if (comp.length && x.foco === null) h += filaFicha(`Promedio por ${per(d)[0]}`, fk(comp.reduce((s, i) => s + en(tot, i, V), 0) / comp.length), '', 'Sólo períodos completos');
  h += filaFicha('% de costo sin descuentos', pc(pctCosto(sumT(tot, T, C), sumT(tot, T, NC))), '', d.ayuda.sin_desc);
  h += filaFicha('Productos con venta', fn(prods.size));
  h += filaFicha('Vendido sin costo cargado', fk(sc), sc > 0.5 ? 'ambar' : '');
  return h;
}

// ── El gráfico ───────────────────────────────────────────────────────────
function htmlGrafico(d, st, x, W, H) {
  const { tr, M, tot, todos, k, MA, totA } = x;
  const mT = 20, mB = 20, mX = 2;
  const n = todos.length, slot = (W - 2 * mX) / Math.max(1, n);
  const pct = st.escala === '%' && k !== 'costo';
  const conAp = !!d.ap && !pct && (k === 'costo' || st.sel === null);
  const bw = Math.max(3, Math.min(46, slot * (conAp ? 0.46 : 0.62))), apw = conAp ? Math.max(2, bw * 0.5) : 0, hueco = conAp ? Math.max(1, Math.min(3, slot * 0.04)) : 0;
  const alc = st.sel !== null ? M.get(st.sel) : tot, alcA = st.sel !== null ? MA.get(st.sel) : totA;
  // Una barra: la pila de los tramos o, en % de costo, un solo valor.
  const vals = todos.map((i) => (k === 'costo' ? [Math.max(0, valor(alc, [i], k) || 0)] : tr.map((t) => Math.max(0, t.miembros.reduce((s, m) => s + valor(M.get(m), [i], k), 0)))));
  const tots = vals.map((r) => r.reduce((s, y) => s + y, 0));
  const aps = todos.map((i) => (conAp && d.ap.nombres[i] ? valor(alcA, [i], k) : NaN));
  const max = pct ? 1 : Math.max(1e-9, ...tots, ...aps.filter((v) => isFinite(v)));
  const y = (v) => mT + (H - mT - mB) * (1 - v / max);
  const cada = Math.max(1, Math.ceil(46 / slot));
  // Cifras: todas si entran; si no, sólo lo clave.
  const rotulos = todos.map((i) => valor(alc, [i], k));
  const claves = new Set();
  if (slot < 46) { const ok = rotulos.map((v, i) => [isFinite(v) ? v : -Infinity, i]); claves.add(ok.reduce((a, b) => (b[0] > a[0] ? b : a))[1]); claves.add(ok.filter((v) => v[0] > -Infinity).reduce((a, b) => (b[0] < a[0] ? b : a), [Infinity, 0])[1]); claves.add(n - 1); }
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(NOM_KPI[k])} por período">`;
  for (let j = 1; j <= 3; j++) { const yy = y((max * j) / 4); s += `<line class="g-guia" x1="${mX}" x2="${W - mX}" y1="${yy}" y2="${yy}"/>`; }
  s += `<line class="g-base" x1="${mX}" x2="${W - mX}" y1="${y(0)}" y2="${y(0)}"/>`;
  todos.forEach((i, j) => {
    const cx = mX + slot * (j + 0.5), ancho = bw + apw + hueco, x0 = cx - ancho / 2, xb = x0 + apw + hueco, on = x.foco === i, parcial = d.periodos[i].parcial;
    s += `<g class="g-col${x.foco !== null && !on ? ' apagada' : ''}" data-i="${i}">`;
    if (on) s += `<rect class="g-foco" x="${cx - slot / 2 + 1}" y="2" width="${Math.max(1, slot - 2)}" height="${H - 4}" rx="6"/>`;
    s += `<rect class="g-hit" x="${cx - slot / 2}" y="0" width="${slot}" height="${H}"/>`;
    if (isFinite(aps[j]) && aps[j] > 0) s += `<rect class="g-ap" x="${x0}" y="${y(aps[j])}" width="${apw}" height="${Math.max(0, y(0) - y(aps[j]))}" rx="${Math.min(3, apw / 2)}"/>`;
    let acu = 0;
    vals[j].forEach((bruto, t) => {
      const v = pct ? (tots[j] ? bruto / tots[j] : 0) : bruto;
      if (v <= 0) return;
      const y1 = y(acu + v), y0 = y(acu), tr1 = k === 'costo' ? null : tr[t];
      const color = k === 'costo' ? (st.sel !== null ? 'var(--accent-deep)' : 'var(--vm-t0)') : st.sel !== null ? (tr1.miembros.includes(st.sel) ? 'var(--accent-deep)' : RESTO) : tr1.color;
      s += `<rect class="t${parcial ? ' parcial' : ''}" x="${xb}" y="${y1}" width="${bw}" height="${Math.max(0, y0 - y1 - 1)}" style="fill:${color}" rx="1.5" data-t="${t}"/>`;
      acu += v;
    });
    if (!pct && (slot >= 46 || claves.has(j) || on)) {
      const top = Math.min(y(tots[j]), isFinite(aps[j]) && aps[j] > 0 && aps[j] > tots[j] && (aps[j] - tots[j]) / max < 0.08 ? y(aps[j]) : y(tots[j]));
      s += `<text class="g-tot" x="${xb + bw / 2}" y="${top - 5}" text-anchor="middle">${esc(unid(st) ? fn(rotulos[j]) : k === 'costo' ? pc(rotulos[j]) : fk(rotulos[j]))}</text>`;
    }
    if (j % cada === 0 || on) s += `<text class="g-eje${on ? ' on' : ''}" x="${cx}" y="${H - 5}" text-anchor="middle">${esc(d.periodos[i].eje)}</text>`;
    s += '</g>';
  });
  return s + '</svg>';
}
function zonaGrafico(raiz, caja) {
  const { data: d, st, x } = raiz.__d;
  const { k, ruta, niv, foco } = x, costo = k === 'costo', pct = st.escala === '%' && !costo;
  const nom = st.sel !== null ? st.sel : (ruta.length ? ruta[ruta.length - 1] : niv[2]);
  const hayParcial = d.periodos.some((p) => p.parcial);
  const conAp = !!d.ap && !pct && (costo || st.sel === null);
  caja.innerHTML = `<div class="vm-zcab"><span class="vm-gtit"><b>${esc(pct ? `Reparto de ${NOM_KPI[k].toLowerCase()}` : NOM_KPI[k])} por ${esc(per(d)[0])}</b> · ${esc(foco !== null ? d.periodos[foco].largo : nom)}${foco === null && hayParcial ? ' · las barras claras están incompletas' : ''}</span>
    ${foco !== null ? '<button type="button" class="vm-quita" data-acc="sinfoco">Ver todo el rango ✕</button>' : ''}<span class="vm-esp"></span>
    ${conAp ? '<span class="vm-ley-ap"><i></i>año pasado</span>' : ''}${costo ? '' : seg([['Monto', 'Monto'], ['%', '% del período']], st.escala, 'escala')}</div><div class="vm-svg" data-zona="svg"></div>`;
  const svg = caja.querySelector('.vm-svg');
  svg.innerHTML = htmlGrafico(d, st, x, Math.max(240, svg.clientWidth || 600), Math.max(150, svg.clientHeight || 240));
  return (costo ? `Costo ÷ venta neta (+ devolución del banco). ` : '') + 'Tocá una barra para fijar el período.';
}

// ── La tabla: grupo › subgrupo › plato en una sola ───────────────────────
function arbol(d, st, x) {
  if (x.arbol) return x.arbol;
  const { lvl, ruta, np } = x;
  const llaveDe = (n) => (pi) => { const c = []; for (let i = lvl; i <= lvl + n; i++) c.push(clave(d, st, pi, i)); return c.join(SEP); };
  const niveles = [];
  for (let n = 0; lvl + n <= 2; n++) niveles.push(acum(d, st, d.filas, llaveDe(n), ruta, np));
  const vive = (a) => x.todos.some((i) => Math.abs(en(a, i, V)) > 0.5 || Math.abs(en(a, i, Q)) > 0.01);
  const hijos = niveles.map((Mn) => { const h = new Map(); for (const [k, a] of Mn.entries()) { if (!vive(a)) continue; const padre = k.includes(SEP) ? k.slice(0, k.lastIndexOf(SEP)) : ''; if (!h.has(padre)) h.set(padre, []); h.get(padre).push(k); } return h; });
  x.arbol = { niveles, hijos, llaveDe };
  return x.arbol;
}
function filasArbol(d, st, x, todas) {
  // `todas`: sin mirar qué está abierto (el Excel baja el árbol entero).
  const A = arbol(d, st, x), salida = [], ko = x.ko;
  const abre = (k, n) => (st.ab[k] !== undefined ? st.ab[k] : n < st.prof);
  const anda = (claves, n, padre) => {
    const orden = (claves || []).slice().sort((p, q) => valor(A.niveles[n].get(q), x.todos, ko) - valor(A.niveles[n].get(p), x.todos, ko));
    for (const k of orden) {
      const a = A.niveles[n].get(k), puede = n + 1 < A.niveles.length && (A.hijos[n + 1].get(k) || []).length > 0, ab = puede && (todas || abre(k, n));
      salida.push({ k, n, a, padre, puede, ab, nom: k.split(SEP).pop() });
      if (ab) anda(A.hijos[n + 1].get(k), n + 1, a);
    }
  };
  anda(A.hijos[0].get(''), 0, x.lvl > 0 ? x.tot : null);
  return salida;
}
function cuentasFila(d, st, x, a, padre) {
  const { todos, ko, totLocal } = x, v = valor(a, todos, ko), g = valor(totLocal, todos, ko), pad = padre ? valor(padre, todos, ko) : NaN;
  return { dentro: padre && pad ? v / pad : NaN, delTotal: g ? v / g : NaN, costo: pctCosto(sumT(a, todos, C), sumT(a, todos, B)), sinDesc: pctCosto(sumT(a, todos, C), sumT(a, todos, NC)) };
}
function zonaTabla(d, st, x) {
  const { tot, todos, k, niv, lvl, foco, ruta, orden, M } = x;
  const costo = k === 'costo', pctPer = st.escala === '%' && !costo;
  const celda = (a, i) => {
    if (pctPer) { const t = valor(tot, [i], k), v = t ? valor(a, [i], k) / t : NaN; return { txt: v ? pc(v) : '—', v }; }
    const v = valor(a, [i], k);
    if (costo) return { txt: pc(v), cls: nivelCosto(d, v), v: NaN };
    return { txt: !isFinite(v) || Math.abs(v) < 0.5 ? '—' : (unid(st) ? fn(v) : fk(v).replace('S/ ', '')), v };
  };
  const maxC = Math.max(1e-9, ...orden.flatMap((n) => todos.map((i) => { const v = celda(M.get(n), i).v; return isFinite(v) ? v : 0; })));
  const calor = (v) => (!isFinite(v) || v <= 0 ? '' : `background-color: color-mix(in srgb, var(--accent) ${Math.round(4 + 30 * Math.min(1, v / maxC))}%, transparent)`);
  const celdas = (a, padre, esTot) => {
    const f = cuentasFila(d, st, x, a, padre);
    let r = '';
    todos.forEach((i) => { const c = celda(a, i); r += `<td class="${c.cls || ''}${foco === i ? ' foco' : ''}" style="${esTot ? '' : calor(c.v)}">${c.txt}</td>`; });
    const t = valor(a, todos, k);
    r += `<td><b>${esc(costo ? pc(t) : unid(st) ? fn(t) : fk(t).replace('S/ ', ''))}</b></td><td>${pc(f.dentro)}</td><td>${pc(f.delTotal)}</td><td class="${nivelCosto(d, f.costo)}">${pc(f.costo)}</td><td>${pc(f.sinDesc)}</td>`;
    return r;
  };
  let h = '<div class="vm-zcab">';
  if (lvl > 0) h += `<button type="button" class="vm-volver" data-acc="subir" data-id="${lvl - 1}">‹ Volver a ${esc(lvl > 1 ? ruta[lvl - 2] : niv[2])}</button>`;
  const niveles = niv[0].slice(lvl);
  if (niveles.length > 1) h += `<span class="vm-rot">Abrir hasta</span>${seg(niveles.map((t, i) => [String(i), t]), String(st.prof), 'prof')}`;
  h += `<span class="vm-esp"></span>${costo ? '' : seg([['Monto', 'Monto'], ['%', '% del período']], st.escala, 'escala')}</div>`;
  h += `<div class="vm-tabla"><table><thead><tr><th>${esc(niv[0][lvl])}</th>`;
  todos.forEach((i) => { const p = d.periodos[i], marca = costo && p.igv; h += `<th class="${foco === i ? 'foco' : ''}"${marca ? ` title="${esc(p.igv)}"` : ''}>${esc(p.eje)}${p.parcial ? '*' : ''}${marca ? ' · IGV' : ''}</th>`; });
  h += `<th>Total</th><th title="Sobre la fila de arriba: un subgrupo sobre su grupo, un plato sobre su subgrupo">% dentro</th><th title="Sobre todo lo que entra en el filtro «Venta»">% del total</th><th title="${esc(d.ayuda.costo)}">% costo</th><th title="${esc(d.ayuda.sin_desc)}">% sin desc.</th></tr></thead><tbody>`;
  h += `<tr class="tot"><td><button type="button" class="tn" data-acc="soltar"><span class="mk"></span><span class="nm">Total${ruta.length ? ` · ${esc(ruta[ruta.length - 1])}` : ''}</span></button></td>${celdas(tot, null, true)}</tr>`;
  for (const f of filasArbol(d, st, x, false)) {
    const on = st.fiT === f.k || (f.n === 0 && st.sel === f.nom && !st.fiT);
    h += `<tr class="n${f.n}${on ? ' sel' : ''}"><td title="${esc(f.nom)}"><button type="button" class="tn" style="padding-left:${6 + f.n * 18}px" data-acc="fila" data-id="${esc(f.k)}" data-n="${f.n}" data-p="${f.puede ? 1 : 0}" data-a="${f.ab ? 1 : 0}" aria-pressed="${on}"${f.puede ? ` aria-expanded="${f.ab}"` : ''}><span class="mk">${f.puede ? (f.ab ? '▾' : '▸') : ''}</span>${f.n === 0 ? `<i style="background:${x.colorDe[f.nom] || RESTO}"></i>` : ''}<span class="nm">${esc(f.nom)}</span></button></td>${celdas(f.a, f.padre, false)}</tr>`;
  }
  h += '</tbody></table></div>';
  const cap = `Mide ${NOM_KPI[k].toLowerCase()}. ▸ abre una fila y un clic en un plato lo muestra en la ficha. «% dentro» es sobre la fila de arriba; «% del total», sobre lo que entra en el filtro «Venta».` +
    (costo ? ` En ámbar pasa del ${pc(d.umbrales[0], 0)} y en rojo del ${pc(d.umbrales[1], 0)}.` : '') + (todos.some((i) => d.periodos[i].parcial) ? ' * período incompleto.' : '');
  return [h, cap];
}
function bajarExcel(raiz) {
  const { data: d, st, x } = raiz.__d, { niv, lvl, todos, k } = x;
  const niveles = niv[0].slice(lvl);
  const cabeza = [...niveles, ...todos.map((i) => d.periodos[i].eje), 'Total', '% dentro', '% del total', '% costo', '% sin desc.'];
  const num = (v) => (isFinite(v) ? v : null), cien = (v) => (isFinite(v) ? v * 100 : null);
  const filas = filasArbol(d, st, x, true).map((f) => {
    const c = cuentasFila(d, st, x, f.a, f.padre), partes = f.k.split(SEP), ini = niveles.map((_, i) => partes[i] || '');
    const mide = (T) => { const v = valor(f.a, T, k); return k === 'costo' ? cien(v) : num(v); };
    return [...ini, ...todos.map((i) => mide([i])), mide(todos), cien(c.dentro), cien(c.delTotal), cien(c.costo), cien(c.sinDesc)];
  });
  bajar(`${archivo(`Mix de carta ${NOM_KPI[k]} ${d.gran}`)}.xlsx`, libro([{ nombre: 'Mix de carta', cabeza, filas }]));
}

// ── Comparación: Qué movió y Mix y costo ─────────────────────────────────
function comparacion(raiz, keyFn) {
  const { data: d, st, x } = raiz.__d;
  const { ruta, iDet, T, TC, foco } = x, np = d.periodos.length;
  const A = acum(d, st, d.filas, keyFn, ruta, np);
  if (st.comp === 'ap') {
    if (!d.ap) return { pendiente: true };
    if (!TC.length) return null;
    const R = acum(d, st, d.ap.filas, keyFn, ruta, np);
    const junta = (ar) => { const s = new Array(NM).fill(0); for (const i of TC) for (let j = 0; j < NM; j++) s[j] += en(ar, i, j); return s; };
    const uno = foco !== null;
    return { a: new Map([...A.entries()].map(([k, ar]) => [k, junta(ar)])), b: new Map([...R.entries()].map(([k, ar]) => [k, junta(ar)])),
      nombreA: uno ? d.periodos[foco].largo : cuando(d, x), nombreB: uno ? d.ap.nombres[foco] : 'los mismos días un año antes', eje: uno ? d.periodos[foco].eje : cuando(d, x), parejo: true };
  }
  void T;
  if (iDet < 1) return null;
  const a = new Map([...A.entries()].map(([k, ar]) => [k, enPer(ar, iDet)]));
  return { a, b: new Map([...A.entries()].map(([k, ar]) => [k, enPer(ar, iDet - 1)])), nombreA: d.periodos[iDet].largo, nombreB: d.periodos[iDet - 1].largo, eje: d.periodos[iDet].eje,
    parejo: !d.periodos[iDet].parcial && !d.periodos[iDet - 1].parcial };
}
function sinComparar(raiz, cmp) {
  const { data: d, x } = raiz.__d;
  if (cmp && cmp.pendiente) { pedirAp(raiz); return ['<div class="vm-vacio">Trayendo el año pasado…</div>', '']; }
  return ['<div class="vm-vacio">No hay con qué comparar este período.</div>', `${cap1(d.periodos[x.iDet].largo)} es el primer período del rango o no tiene año pasado.`];
}
function selectorComp(d, st, x) {
  return seg([['ap', 'Año pasado'], ['ant', 'Período anterior']], st.comp, 'comp', x.TC.length || !d.ap ? {} : { ap: 'Sin año pasado para este período' });
}
function zonaMovio(raiz) {
  const { data: d, st, x } = raiz.__d;
  const cab = `<div class="vm-zcab">${selectorComp(d, st, x)}${seg([['Monto', 'Monto'], ['Mix', 'Mix (pp)']], st.cambio, 'cambio')}</div>`;
  const cmp = comparacion(raiz, (pi) => clave(d, st, pi, x.lvl));
  if (!cmp || cmp.pendiente) { const [h, t] = sinComparar(raiz, cmp); return [cab + h, t]; }
  const ko = x.ko, usaPP = st.cambio === 'Mix';
  let tA = 0, tB = 0;
  const nombres = new Set([...cmp.a.keys(), ...cmp.b.keys()]);
  const mv = (m, n) => { const ar = m.get(n); return ar ? deFila(ar, ko) : 0; };
  for (const n of nombres) { tA += mv(cmp.a, n); tB += mv(cmp.b, n); }
  const filas = [...nombres].map((n) => { const va = mv(cmp.a, n), vb = mv(cmp.b, n); return { n, va, vb, d: va - vb, pp: (tA ? va / tA : 0) - (tB ? vb / tB : 0) }; })
    .filter((f) => Math.abs(f.va) + Math.abs(f.vb) > 0.5);
  const kk = usaPP ? 'pp' : 'd';
  filas.sort((p, q) => Math.abs(q[kk]) - Math.abs(p[kk]));
  const top = filas.slice(0, 10), resto = filas.slice(10);
  if (resto.length) top.push({ n: `Resto (${resto.length})`, resto: true, va: resto.reduce((s, f) => s + f.va, 0), vb: resto.reduce((s, f) => s + f.vb, 0), d: resto.reduce((s, f) => s + f.d, 0), pp: resto.reduce((s, f) => s + f.pp, 0) });
  const mx = Math.max(1e-9, ...top.map((f) => Math.abs(f[kk])));
  const und = ko === 'und', fm = (v) => (und ? fn(Math.abs(v)) : fk(Math.abs(v)));
  const filasH = top.map((f) => {
    const w = (45 * Math.abs(f[kk])) / mx, pos = f[kk] >= 0;
    const bar = `<i class="${pos ? 'p' : 'm'}" style="${pos ? 'left:50%' : `left:${50 - w}%`};width:${w}%"></i>`;
    const txt = usaPP ? `${pp(f.pp)}<small>${pc(tA ? f.va / tA : NaN, 0)}</small>` : `${conSigno(f.d, fm(f.d))}<small>${f.vb > 0 ? conSigno(f.va / f.vb - 1, pc(Math.abs(f.va / f.vb - 1), 0)) : 'nuevo'}</small>`;
    return `<div class="mv-f${f.resto ? ' resto' : ''}"${f.resto ? '' : ` data-acc="sel" data-id="${esc(f.n)}"`} title="${esc(f.n)}: ${esc(fmedK(ko, f.vb))} → ${esc(fmedK(ko, f.va))}"><span class="n">${esc(f.n)}</span><span class="mv-bar">${bar}</span><span class="v">${txt}</span></div>`;
  }).join('');
  const P2 = comparacion(raiz, (pi) => d.prods[pi][2] + '\u0001' + d.prods[pi][1]);
  const prods = [...P2.a.entries()].map(([k, ar]) => ({ k, va: deFila(ar, ko), vb: P2.b.get(k) ? deFila(P2.b.get(k), ko) : 0 })).filter((y) => y.va > 0.5).sort((p, q) => q.va - p.va).slice(0, 12);
  const topH = prods.map((y, r) => {
    const [n, sub] = y.k.split('\u0001'), p = varPct(y.va, y.vb);
    return `<div class="top-f"><span class="r">${r + 1}</span><span class="n" title="${esc(n)}">${esc(n)}<small>${esc(sub)}</small></span><span class="v">${esc(fmedK(ko, y.va))}</span><span class="v ${isFinite(p) ? (p >= 0 ? 'verde' : 'rojo') : 'gris'}">${isFinite(p) ? conSigno(p, pc(Math.abs(p), 0)) : 'nuevo'}</span></div>`;
  }).join('');
  const html = `${cab}<div class="mv"><div class="mv-caja"><div class="mv-tit">Qué movió ${esc(cmp.eje)}<span>${usaPP ? 'puntos del total' : (und ? 'unidades' : 'soles')}</span></div>${filasH}</div>
    <div class="mv-caja"><div class="mv-tit">Lo más vendido en ${esc(cmp.eje)}<span>vs ${st.comp === 'ap' ? 'año pasado' : 'anterior'}</span></div>${topH}</div></div>`;
  const dT = tA - tB;
  const res = `${conSigno(dT, und ? `${fn(Math.abs(dT))} und` : fk(Math.abs(dT)))}${tB ? ` (${conSigno(dT / tB, pc(Math.abs(dT / tB)))})` : ''}`;
  let cap = `${cap1(cmp.nombreA)} contra ${cmp.nombreB}: ${res}.`;
  if (!cmp.parejo) cap += ` Un período está incompleto en el rango: ${usaPP ? 'se compara el reparto, no el monto.' : 'el monto no se compara parejo; el mix sí.'}`;
  return [html, cap];
}

function zonaMix(raiz) {
  const { data: d, st, x } = raiz.__d;
  const cab = `<div class="vm-zcab">${selectorComp(d, st, x)}</div>`;
  const cmp = comparacion(raiz, (pi) => `${clave(d, st, pi, x.lvl)}\u0001${d.prods[pi][2]}\u0001${d.prods[pi][1]}`);
  if (!cmp || cmp.pendiente) { const [h, t] = sinComparar(raiz, cmp); return [cab + h, t]; }
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
  const html = `${cab}<div class="mc">${frase}<div class="mc-dos">
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
  caja.innerHTML = `<div class="vm-zcab">${seg([['costo', 'Color: % costo'], ['grupo', `Color: ${niv[1][lvl]}`]], st.color, 'color')}</div><div class="mapa"></div><div class="leyenda-mapa">${st.color === 'costo'
    ? '<span><i class="tc1"></i>hasta 25 %</span><span><i class="tc2"></i>25–35 %</span><span><i class="tc3"></i>35–45 %</span><span><i class="tc4"></i>45–70 %</span><span><i class="tc5"></i>más de 70 %</span><span><i class="tc0"></i>sin costo cargado</span>'
    : `<span>Cada tono es un ${esc(niv[1][lvl])}, en el orden de la lista.</span>`}</div>`;
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
      const sty = st.color === 'costo' ? '' : `background:color-mix(in srgb, ${colorDe[t.padre || t.n] || 'var(--accent)'} ${t.padre ? 62 : 80}%, var(--bg-card));`;
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
    .filter((f) => Math.abs(f.v) > 0.005 || Math.abs(f.c) > 0.005 || Math.abs(f.b) > 0.005 || Math.abs(f.sc) > 0.005);
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
    raiz.innerHTML = `<div class="vm-top"><span data-zona="ojo"></span><span data-zona="va"></span><input class="vm-buscar" data-acc="buscar" list="vm-prods" placeholder="Buscar un producto…" autocomplete="off" aria-label="Buscar un producto"><button type="button" class="vm-excel" data-acc="excel" title="Baja la tabla entera, con sus tres niveles">Excel ↓</button></div>
      <div class="vm-kpis" data-zona="kpis"></div><div class="vm-pie" data-zona="pie"></div>
      <div class="vm-cuerpo"><div class="vm-izq"><div class="vm-zona" data-zona="zona"></div><div class="vm-cap" data-zona="cap"></div></div>
      <aside class="vm-panel" aria-label="Lista y ficha"><div class="vm-ruta" data-zona="ruta"></div><div class="vm-lista" data-zona="lista"></div><div class="vm-ficha" data-zona="ficha"></div></aside></div>
      <datalist id="vm-prods"></datalist><div class="vm-tip" data-zona="tip"></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  const x = calcular(raiz);
  z('kpis').innerHTML = htmlKpis(d, st, x);
  z('ojo').innerHTML = htmlOjo(d, st, x);
  const ui = raiz.__d.va || {};
  const firmaVa = `${JSON.stringify(st.va)}|${ui.abierto}|${ui.q}|${[...(ui.exp || [])]}`;
  if (raiz.__d.A && raiz.__d.ctrlFirma !== firmaVa) {
    z('va').innerHTML = window.VentasAlcance.html(raiz.__d.A, st.va, raiz.__d.va);
    raiz.__d.ctrlFirma = firmaVa;
    const q = raiz.querySelector('.va-q');
    if (q && raiz.__d.enfocarVa) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
    raiz.__d.enfocarVa = false;
  }
  z('pie').innerHTML = htmlPie(d, st);
  z('ruta').innerHTML = htmlRuta(d, st, x);
  const lista = z('lista'), yLista = lista.scrollTop;
  lista.innerHTML = htmlLista(d, st, x);
  lista.scrollTop = yLista;
  z('ficha').innerHTML = htmlFicha(d, st, x);
  dibujarZona(raiz);
}
function dibujarZona(raiz) {
  const { data: d, st } = raiz.__d;
  const caja = raiz.querySelector('[data-zona="zona"]'), cap = raiz.querySelector('[data-zona="cap"]');
  const y = caja.querySelector('.vm-tabla')?.scrollTop || 0, xx = caja.querySelector('.vm-tabla')?.scrollLeft || 0;
  let html = '', texto = '';
  if (st.zona === 'Graf') { texto = zonaGrafico(raiz, caja); cap.textContent = texto + (d.nota ? ` ${d.nota}` : ''); return; }
  if (st.zona === 'Mapa') { texto = zonaMapa(raiz, caja); cap.textContent = texto + (d.nota ? ` ${d.nota}` : ''); return; }
  if (st.zona === 'Movio') [html, texto] = zonaMovio(raiz);
  else if (st.zona === 'Mix') [html, texto] = zonaMix(raiz);
  else if (st.zona === 'Calculo') [html, texto] = zonaCalculo(raiz);
  else [html, texto] = zonaTabla(d, st, raiz.__d.x);
  caja.innerHTML = html;
  cap.textContent = texto + (d.nota ? ` ${d.nota}` : '');
  const t = caja.querySelector('.vm-tabla');
  if (t && raiz.__d.mismaZona) { t.scrollTop = y; t.scrollLeft = xx; }
}
function recordar(st) {
  guardar(CLAVE, { eje: st.eje, kpi: st.kpi, escala: st.escala, zona: st.zona, cambio: st.cambio, comp: st.comp, color: st.color, ruta: st.ruta, prof: st.prof });
}
function llenarBuscador(raiz) {
  const d = raiz.__d.data, tot = new Map();
  for (const r of d.filas) tot.set(r[0], (tot.get(r[0]) || 0) + r[2 + V]);
  const ids = [...tot.keys()].filter((pi) => tot.get(pi) > 0.5).sort((a, b) => tot.get(b) - tot.get(a));
  raiz.__d.buscar = new Map(ids.map((pi) => [`${d.prods[pi][2]} · ${d.prods[pi][1]}`, pi]));
  raiz.querySelector('#vm-prods').innerHTML = [...raiz.__d.buscar.keys()].map((k) => `<option value="${esc(k)}"></option>`).join('');
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
    // El filtro «Venta»: otra elección recorta los datos y redibuja todo.
    const va = ev.target.closest('[data-va]'), R = raiz.__d;
    if (va && raiz.contains(va) && R.A) {
      if (va.dataset.va === 'q') return;
      const antes = R.st.va, nueva = window.VentasAlcance.accion(R.A, antes, R.va, va);
      if (!window.VentasAlcance.igual(antes, nueva)) { R.st.va = nueva; R.st.sel = null; R.st.fiT = null; conAlcance(raiz); llenarBuscador(raiz); }
      dibujar(raiz);
      return;
    }
    if (R.va && R.va.abierto && !ev.target.closest('.va')) { R.va.abierto = false; R.va.q = ''; dibujar(raiz); }
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
    if (b.tagName === 'INPUT' || b.tagName === 'SELECT') return;
    const acc = b.dataset.acc, id = b.dataset.id;
    ev.stopPropagation();
    if (acc === 'bajar') { st.ruta = st.ruta.concat(id); st.sel = null; st.fiT = null; }
    else if (acc === 'sel') { st.sel = st.sel === id && !st.fiT ? null : id; st.fiT = null; raiz.__d.mismaZona = true; }
    else if (acc === 'subir') { st.ruta = st.ruta.slice(0, +id); st.sel = null; st.fiT = null; }
    else if (acc === 'soltar') { st.sel = null; st.fiT = null; raiz.__d.mismaZona = true; }
    else if (acc === 'sinfoco') st.foco = null;
    else if (acc === 'kpi') { st.kpi = id; raiz.__d.mismaZona = true; }
    else if (acc === 'ojo') { st.zona = 'Calculo'; st.ruta = []; st.sel = null; st.fiT = null; }
    else if (acc === 'excel') { bajarExcel(raiz); return; }
    else if (acc === 'prof') { st.prof = +id; st.ab = {}; raiz.__d.mismaZona = true; }
    else if (acc === 'fila') {
      // Elegir en la tabla no la achica: abre o cierra y cambia la ficha.
      const n = +b.dataset.n, puede = b.dataset.p === '1', ab = b.dataset.a === '1', nom = id.split(SEP).pop();
      raiz.__d.mismaZona = true;
      if (puede) { st.ab = Object.assign({}, st.ab, { [id]: !ab }); if (n === 0) { st.sel = nom; st.fiT = null; } else st.fiT = id; }
      else if (n === 0) { st.sel = st.sel === nom ? null : nom; st.fiT = null; }
      else st.fiT = st.fiT === id ? null : id;
    }
    else if (acc === 'mapa') { ocultarTip(); if (b.dataset.p) { st.ruta = st.ruta.concat(b.dataset.p); } st.sel = id; st.fiT = null; }
    else if (acc === 'prod') { const [l0, sub, n] = JSON.parse(id); st.ruta = [l0, sub]; st.sel = n; st.fiT = null; }
    else if (acc === 'carta') { raiz.__d.enviar('carta', { cod: id, n: Date.now() }); return; }
    else if (acc === 'comp') { st.comp = id; if (id === 'ap' && !d.ap) pedirAp(raiz); }
    else if (['escala', 'zona', 'cambio', 'color'].includes(acc)) st[acc] = id;
    else return;
    recordar(st);
    dibujar(raiz);
  });
  raiz.addEventListener('change', (ev) => {
    const acc = ev.target.dataset.acc, R = raiz.__d, st = R.st, d = R.data;
    if (acc === 'eje') { if (ev.target.value !== st.eje) { st.eje = ev.target.value; st.ruta = []; st.sel = null; st.fiT = null; st.ab = {}; st.prof = 0; } recordar(st); dibujar(raiz); return; }
    if (acc === 'medir') { st.kpi = ev.target.value === 'und' ? 'und' : (st.kpi === 'margen' ? 'margen' : 'venta'); R.mismaZona = true; recordar(st); dibujar(raiz); return; }
    if (acc === 'gran') { if (ev.target.value !== d.gran) { st.foco = null; R.enviar('gran', ev.target.value); } return; }
    if (acc !== 'buscar') return;
    const pi = R.buscar && R.buscar.get(ev.target.value);
    if (pi === undefined) return;
    st.ruta = [clave(d, st, pi, 0), d.prods[pi][1]]; st.sel = d.prods[pi][2]; st.fiT = null;
    ev.target.value = '';
    recordar(st); dibujar(raiz);
  });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.va === 'q') { raiz.__d.va.q = ev.target.value; raiz.__d.enfocarVa = true; dibujar(raiz); return; }
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
    const i = +col.dataset.i, k = x.k, a = st.sel !== null ? x.M.get(st.sel) : x.tot, aA = st.sel !== null ? x.MA.get(st.sel) : x.totA, t = valor(x.tot, [i], k), r = ev.target.closest('rect.t');
    const apTxt = d.ap && d.ap.nombres[i] ? `<br>Año pasado: ${esc(fmedK(k, valor(aA, [i], k)))} (${esc(d.ap.nombres[i])})` : '';
    if (r && k !== 'costo') {
      const tr = x.tr[+r.dataset.t], v = tr.miembros.reduce((s, m) => s + valor(x.M.get(m), [i], k), 0);
      mostrarTip(ev, `<b>${esc(tr.nombre)}</b>${esc(d.periodos[i].largo)}<br>${esc(fmedK(k, v))} · ${pc(t ? v / t : NaN)} del período`);
    } else mostrarTip(ev, `<b>${esc(d.periodos[i].largo)}</b>${esc(fmedK(k, valor(a, [i], k)))}${apTxt}`);
  });
  raiz.addEventListener('mouseleave', ocultarTip);
  // Otro ancho, otra barra y otro mapa (se dibujan al ancho de su caja).
  let espera = null;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => { if (raiz.isConnected) dibujar(raiz); }, 150); });
}

// Los datos de la tarjeta con el filtro «Venta» aplicado: las filas (y las
// del año pasado) de los productos cuyo grupo y subgrupo se cuentan.
function conAlcance(raiz) {
  const R = raiz.__d, f = R.full, VA = window.VentasAlcance;
  if (!R.A || !VA || !R.st.va) { R.data = f; return; }
  const sel = R.st.va, ok = f.prods.map((p) => VA.pasa(sel, p[0], p[1]));
  R.data = Object.assign({}, f, {
    alcanceRot: VA.etiqueta(R.A, sel),
    filas: f.filas.filter((r) => ok[r[0]]),
    ap: f.ap ? Object.assign({}, f.ap, { filas: f.ap.filas.filter((r) => ok[r[0]]) }) : f.ap,
  });
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
      st: Object.assign({ eje: 'Carta', kpi: 'venta', escala: 'Monto', zona: 'Graf', cambio: 'Monto', comp: 'ap', color: 'costo', ruta: [], prof: 0 },
        leer(CLAVE, {}), { foco: null, sel: null, calc: '', ab: {}, fiT: null }),
    };
    if (!Array.isArray(raiz.__d.st.ruta)) raiz.__d.st.ruta = [];
    enlazar(raiz);
  }
  const prev = raiz.__d.full;
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.full = data;
  const VA = window.VentasAlcance;
  if (data.alcance && VA) {
    const viejo = raiz.__d.A;
    raiz.__d.A = data.alcance;
    if (!raiz.__d.va) raiz.__d.va = VA.nuevaUi();
    if (raiz.__d.st.va === undefined) raiz.__d.st.va = VA.inicio(data.alcance);
    else if (JSON.stringify(viejo) !== JSON.stringify(data.alcance)) raiz.__d.st.va = VA.reubicar(viejo, data.alcance, raiz.__d.st.va);
  }
  conAlcance(raiz);
  if (data.ap) raiz.__d.apPedido = true;
  if (!prev || prev.filas !== data.filas) { raiz.__d.ctrlFirma = null; }
  dibujar(raiz);
  llenarBuscador(raiz);
  // El año pasado llega después: la tarjeta no lo espera.
  if (!data.ap) setTimeout(() => { if (raiz.isConnected && !raiz.__d.full.ap) pedirAp(raiz); }, 300);
}
