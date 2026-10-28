// Consumo según ventas como componente nativo; misma cuenta de referencia (#733).
// Desde la regla #751: la cuenta de cada porcionamiento, «Rendimiento» (90 días
// o último mes, que pide a Python) y la merma esperada, que se guarda en R2.
export default function(component){
  const previous=window.__consumoNative;previous?.cleanup();
  const {parentElement}=component,owner=parentElement.ownerDocument;
  let raiz=parentElement.querySelector('.consumo-pieza');
  if(!raiz){raiz=owner.createElement('div');raiz.className='consumo-pieza';parentElement.appendChild(raiz);}
  raiz.innerHTML='<div class="ccn-acciones"><span id="ccn-seleccion"></span><button id="ccn-excel" type="button">Excel de esta vista ↓</button></div><div class="consumo-contenido">'+/*__HTML__*/null+'</div>';
  const document={getElementById:id=>raiz.querySelector('#'+CSS.escape(id)),querySelector:s=>raiz.querySelector(s),querySelectorAll:s=>raiz.querySelectorAll(s)};
  const abort=new AbortController(),observers=[];
  const alto=()=>{const h=Math.max(320,Math.round(window.innerHeight*.62))+'px';if(raiz.style.getPropertyValue('--alto-tabla')!==h)raiz.style.setProperty('--alto-tabla',h);};alto();
  window.addEventListener('resize',alto,{signal:abort.signal});

const D = component.data.datos;
const P = D.periodo;
const MESES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const DIAS = ['lun','mar','mié','jue','vie','sáb','dom'];
const DIAS_L = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo'];
const fecha = s => { const [a, m, d] = s.slice(0, 10).split('-').map(Number); return { a, m, d }; };
const fCorta = s => { const f = fecha(s); return `${f.d} ${MESES[f.m - 1]}`; };
const fMes = s => { const f = fecha(s); return `${MESES[f.m - 1]} ${f.a}`; };
const corta = u => ({ KILOS: 'kg', LITROS: 'L', UND: 'und', UNIDAD: 'und' }[u] || String(u || '').toLowerCase());
const n0 = v => Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
const dec = (v, d) => Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
// Una cantidad o un promedio: los decimales dependen del tamaño, no de la unidad.
const prom = v => !v ? '—' : dec(v, Math.abs(v) >= 100 ? 0 : (Math.abs(v) >= 10 ? 1 : 2));
const sol = v => 'S/ ' + (Math.abs(v) >= 10 ? n0(v) : dec(v, 2));
const fS = v => !v ? '—' : (Math.abs(v) >= 10 ? n0(v) : dec(v, 1));
const pct = (v, t) => t ? dec(100 * v / t, 1) + '%' : '—';
const pct0 = (v, t) => t ? Math.round(100 * v / t) + '%' : '—';
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cap = s => s ? s[0] + s.slice(1).toLowerCase() : '';
const suma = a => { let s = 0; for (const x of a) s += x; return s; };
const tono = (r, tope, fondo) => r <= 0 ? fondo : `color-mix(in srgb, var(--acento) ${Math.round(tope * r)}%, ${fondo})`;
const esAlmuerzo = h => h >= 6 && h < 17;
const CHEV = '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 2.5 8 6l-3.5 3.5"/></svg>';

// ── estado de la vista (se recuerda mientras dure la pestaña) ──
const K_UI = 'consumo_recetas_ui';
let UI = { vista: 'tabla', tdCols: 'semana', tdVal: 'cant', vi: true, modo: 'dias', sel: null };
try { Object.assign(UI, JSON.parse(window.sessionStorage.getItem(K_UI) || '{}')); } catch (e) {}
if (!['tabla', 'resumen', 'compras'].includes(UI.vista)) UI.vista = 'tabla';
if (!['dias','horas','semanas'].includes(UI.modo)) UI.modo='dias';
if (!['cant','soles'].includes(UI.tdVal)) UI.tdVal='cant';
UI.vi=UI.vi!==false;
const texto=v=>typeof v==='string'?v:'';
const guardar = () => { try { window.sessionStorage.setItem(K_UI, JSON.stringify(UI)); } catch (e) {} };

// ── las cubetas ──
const NF = P.finas.length, NM = P.meses.length, NH = D.horas.length;
const dUTC = s => Date.parse(s + 'T00:00:00Z');
const lunesDe = s => { const t = dUTC(s); const d = (new Date(t).getUTCDay() + 6) % 7; return t - d * 864e5; };
// Día por día, la semana de cada día; por semana, cada cubeta ya es una semana.
const LUNES = [...new Set(P.finas.map(lunesDe))].sort((a, b) => a - b);
const semIdx = P.grano === 'dia' ? P.finas.map(f => LUNES.indexOf(lunesDe(f))) : P.finas.map((_, i) => i);
const NS = P.grano === 'dia' ? LUNES.length : NF;
const semLbl = LUNES.map(t => { const s = new Date(t).toISOString().slice(0, 10); return s < P.desde ? P.desde : s; });
const diasSem = LUNES.map(t => { let n = 0; for (let k = 0; k < 7; k++) { const s = new Date(t + k * 864e5).toISOString().slice(0, 10); if (s >= P.desde && s <= P.hasta) n++; } return n; });
const semParcial = i => P.grano === 'dia' ? diasSem[i] < 7 : (i === 0 && lunesDe(P.desde) < dUTC(P.desde)) || (i === NF - 1 && lunesDe(P.hasta) + 6 * 864e5 > dUTC(P.hasta));
const semTitulo = i => P.grano === 'dia' ? semLbl[i] : (i === 0 ? P.desde : P.finas[i]);
const PLATOS = D.platos;
const CAMINOS = D.caminos;
const CAM_GRUPO = c => c === 'directo en el plato' ? 'directo' : (c === 'receta base' ? 'receta' : (c === 'porcionamiento' ? 'porc' : 'mixto'));
const GRUPOS = {
  porc: { txt: 'Por porcionamiento', col: 'var(--c-porc)' },
  receta: { txt: 'Dentro de recetas base', col: 'var(--c-receta)' },
  directo: { txt: 'Directo en el plato', col: 'var(--c-directo)' },
  mixto: { txt: 'Porcionamiento y receta base', col: 'var(--c-mixto)' },
};
const prepNombre = p => p ? (D.preps[p] ? D.preps[p][0] : p) : 'Directo en la receta del plato';
const prepEtiqueta = p => {
  if (!p) return `${esc(prepNombre(p))}<span class="t-di">directo</span>`;
  const t = D.preps[p] ? D.preps[p][1] : '';
  return `${esc(prepNombre(p))}<span class="${t === 'porcionado' ? 't-po' : 't-rb'}">${t || 'preparación'}</span>`;
};

// ── el árbol, con o sin venta interna ──
const ARBOL = {};
const vec = () => ({ v: new Float64Array(NF), m: new Float64Array(NM), ds: new Float64Array(7), t: new Float64Array(2), tot: 0 });
const sumar = (x, f) => {
  for (const [i, q] of f[6]) x.v[i] += q;
  for (const [i, q] of f[7]) x.m[i] += q;
  for (let k = 0; k < 7; k++) x.ds[k] += f[8][k];
  x.t[0] += f[9][0]; x.t[1] += f[9][1];
  x.tot += f[9][0] + f[9][1];
};
function arbolDe(conVI) {
  const k = conVI ? 'si' : 'no';
  if (ARBOL[k]) return ARBOL[k];
  const ins = new Map();
  for (const f of D.filas) {
    const [cod, prep, pid, n1, ci, ui] = f;
    const interna = PLATOS[pid][1];
    if (!conVI && interna) continue;
    let a = ins.get(cod);
    if (!a) ins.set(cod, a = Object.assign(vec(), { cod, preps: new Map(), cam: new Map(), porc: new Map(), vi: 0, pl: new Map() }));
    let b = a.preps.get(prep);
    if (!b) a.preps.set(prep, b = Object.assign(vec(), { prep, platos: new Map() }));
    let c = b.platos.get(pid);
    if (!c) b.platos.set(pid, c = Object.assign(vec(), { pid, n1: new Set() }));
    if (n1) c.n1.add(n1);
    sumar(a, f); sumar(b, f); sumar(c, f);
    const q = f[9][0] + f[9][1];
    const g = CAM_GRUPO(CAMINOS[ci]);
    a.cam.set(g, (a.cam.get(g) || 0) + q);
    if (ui === 2) a.porc.set(prep, (a.porc.get(prep) || 0) + q);
    if (interna) a.vi += q;
    a.pl.set(pid, (a.pl.get(pid) || 0) + q);
  }
  const lista = [...ins.values()].map(a => Object.assign(a, { costo: a.tot * D.insumos[a.cod][2] }))
    .sort((x, y) => y.costo - x.costo);
  return (ARBOL[k] = { ins, lista });
}
let A = arbolDe(UI.vi);

// ── resumen de arriba ──
function pintarResumen() {
  const costo = suma(A.lista.map(a => a.costo));
  document.getElementById('k-costo').textContent = sol(costo);
  document.getElementById('k-sub').textContent =
    `${n0(A.lista.length)} insumos · fecha del pedido · recetas abiertas hasta ${D.resumen.niveles} niveles` + (UI.vi ? ' · venta interna con fecha de producción cuando corresponde' : ' · sin venta interna');
  const g = new Map();
  for (const a of A.lista) for (const [k, q] of a.cam) g.set(k, (g.get(k) || 0) + q * D.insumos[a.cod][2]);
  const gr = [...g.entries()].sort((x, y) => y[1] - x[1]);
  const tot = suma(gr.map(x => x[1]));
  document.getElementById('k-barra').innerHTML = gr.map(([k, v]) =>
    `<span style="width:${100 * v / (tot || 1)}%;background:${GRUPOS[k].col}" title="${GRUPOS[k].txt}"></span>`).join('');
  document.getElementById('k-leyenda').innerHTML = gr.map(([k, v]) =>
    `<span><i style="background:${GRUPOS[k].col}"></i>${GRUPOS[k].txt} <b>${pct(v, tot)}</b></span>`).join('');
  const cd = [0, 0, 0, 0, 0, 0, 0]; let al = 0, ce = 0;
  for (const a of A.lista) {
    const pr = D.insumos[a.cod][2];
    for (let k = 0; k < 7; k++) cd[k] += a.ds[k] * pr;
    al += a.t[0] * pr; ce += a.t[1] * pr;
  }
  const cdp = cd.map((v, k) => P.n_dia[k] ? v / P.n_dia[k] : 0);
  const mx = Math.max(...cdp, 1e-9), mn = Math.min(...cdp.filter((_, k) => P.n_dia[k])), ip = cdp.indexOf(mx), im = cdp.indexOf(mn);
  document.getElementById('k-dias').innerHTML = cdp.map((v, i) =>
    `<div class="dr${i === ip ? ' pico' : ''}" title="${DIAS_L[i]}: ${sol(v)} por día en promedio"><i style="height:${Math.max(2, 40 * v / mx)}px"></i><span>${DIAS[i]}</span></div>`).join('');
  document.getElementById('k-cuando').innerHTML =
    `El <b>${DIAS_L[ip]}</b> se consume ${sol(mx)} por día; el ${DIAS_L[im]}, ${sol(mn)}. La cena lleva el ${pct0(ce, al + ce)}.`;
  // Lo comprado, arriba (regla #751): antes sólo estaba en su pestaña.
  const kc = document.getElementById('k-comp'), kb = document.getElementById('k-comp-barra'), ks = document.getElementById('k-comp-sub');
  if (!D.compras_familias.length) { kc.textContent = '—'; kb.innerHTML = ''; ks.textContent = 'No se pudieron leer las compras del período.'; }
  else {
    const comp = filasCompras().filter(r => r.comp > 0), sT = suma(comp.map(r => r.sComp));
    const sin = comp.filter(r => r.usado <= 0), sS = suma(sin.map(r => r.sComp));
    kc.textContent = sol(sT);
    kb.innerHTML = `<span style="width:${100 * (sT - sS) / (sT || 1)}%;background:var(--acento)" title="Lo usó alguna venta"></span><span style="width:${100 * sS / (sT || 1)}%;background:var(--adv-borde)" title="Ninguna venta lo usó"></span>`;
    ks.textContent = sin.length ? `${sol(sS)} en ${sin.length} producto${sin.length === 1 ? '' : 's'} que ninguna venta del período usó.` : 'Todo lo comprado lo usó alguna venta del período.';
  }
}

// ── la venta interna ──
{
  const vi = D.venta_interna;
  document.getElementById('vi-cuenta').textContent = vi.pedidos ? `· ${vi.platos} plato${vi.platos === 1 ? '' : 's'}` : '· no hubo';
  document.getElementById('vi-lbl').title = vi.pedidos
    ? `${vi.nombres.join(', ')}: lo que se produce en casa para Mayta —el chorizo, la chistorra y la manteca de pato— cuenta el día que se PRODUJO y no el que se facturó: se factura por tanda (en agosto de 2026, nada; el 23 de septiembre, 600 unidades) y así el magret «se usaba» un mes después de comprado. Si sale de porcionar una masa que se hace con orden de producción, la fecha es la de esa orden; si no, la de su porcionamiento. Si también va al salón, la venta interna se lleva su parte de los últimos 12 meses. Lo que se revende tal cual (vinos, panceta) sigue por la factura. Igual va por tanda y corre el patrón de días y horas: es la misma que apaga Ventas › Por hora.`
    : 'En el período no hubo venta interna.';
  const cb = document.getElementById('vi');
  cb.checked = UI.vi;
  cb.addEventListener('change', () => {
    UI.vi = cb.checked; guardar();
    A = arbolDe(UI.vi);
    if (UI.sel && !A.ins.has(UI.sel)) UI.sel = null;
    pintarTodo();
  });
}

// ── pestañas ──
const tabs = document.getElementById('vistas');
function pintarVista() {
  tabs.querySelectorAll('button').forEach(b => b.setAttribute('aria-selected', b.dataset.v === UI.vista));
  document.getElementById('dinamica').hidden = UI.vista !== 'tabla';
  document.getElementById('vista-resumen').hidden = UI.vista !== 'resumen';
  document.getElementById('vista-compras').hidden = UI.vista !== 'compras';
}
tabs.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  UI.vista = b.dataset.v; guardar(); pintarVista();
  pintarActiva();
});

// ═══ TABLA DINÁMICA ═══
// El ancho VISIBLE de la tabla: la fila de los porcionamientos mide eso y
// queda pegada a la izquierda aunque las columnas se deslicen.
{
  const wrap = document.querySelector('.td-wrap');
  const ro=new ResizeObserver(()=>{const w=wrap.clientWidth+'px';if(wrap.clientWidth&&wrap.style.getPropertyValue('--td-vis')!==w)wrap.style.setProperty('--td-vis',w);});observers.push(ro);ro.observe(wrap);
}
const COLS = [['total', 'Total'], ['semana', 'Semana']];
if (P.grano === 'dia') COLS.push(['dia', 'Día']);
if (NM > 1) COLS.push(['mes', 'Mes']);
COLS.push(['dsem', 'Día de la semana'], ['turno', 'Turno']);
if (!COLS.some(c => c[0] === UI.tdCols)) UI.tdCols = 'semana';
document.getElementById('td-cols').innerHTML = COLS.map(([k, t]) => `<button type="button" data-c="${k}">${t}</button>`).join('');
let tdTxt = texto(UI.tdTxt), tdFam = texto(UI.tdFam)||'Todas';
const tdAbiertos = new Set(Array.isArray(UI.abiertos)?UI.abiertos.filter(k=>typeof k==='string'):[]);
document.getElementById('td-buscar').value=tdTxt;
function cubetas(x) {
  switch (UI.tdCols) {
    case 'semana': { const s = new Array(NS).fill(0); for (let i = 0; i < NF; i++) s[semIdx[i]] += x.v[i]; return s; }
    case 'dia': return Array.from(x.v);
    case 'mes': return Array.from(x.m);
    case 'dsem': return Array.from(x.ds, (q, k) => P.n_dia[k] ? q / P.n_dia[k] : 0);
    case 'turno': return [x.t[0], x.t[1]];
    default: return [];
  }
}
function tdCabeza() {
  let cols = [];
  if (UI.tdCols === 'semana') cols = Array.from({ length: NS }, (_, i) => `<th class="b">${fCorta(semTitulo(i))}${semParcial(i) ? '*' : ''}<span class="dsub">semana</span></th>`);
  if (UI.tdCols === 'dia') cols = P.finas.map((f, i) => { const x = fecha(f); const d = (new Date(dUTC(f)).getUTCDay() + 6) % 7; return `<th class="b">${DIAS[d]}<span class="dsub">${i === 0 || x.d === 1 ? fCorta(f) : x.d}</span></th>`; });
  if (UI.tdCols === 'mes') cols = P.meses.map(m => `<th class="b">${fMes(m)}<span class="dsub">mes</span></th>`);
  if (UI.tdCols === 'dsem') cols = DIAS.map((d, j) => `<th class="b">${d}<span class="dsub">prom. de ${P.n_dia[j]}</span></th>`);
  if (UI.tdCols === 'turno') cols = ['<th class="b">Almuerzo<span class="dsub">antes de 17 h</span></th>', '<th class="b">Cena<span class="dsub">desde 17 h</span></th>'];
  document.getElementById('td-cab').innerHTML =
    `<tr><th class="c-nom">Insumo de compra › preparación › plato</th><th class="c-tot">${UI.tdVal === 'soles' ? 'Soles' : 'Cantidad'}<span class="dsub">del período</span></th>${cols.join('')}</tr>`;
}
function celdasTD(x, factor) {
  const cs = cubetas(x).map(q => q * factor);
  if (!cs.length) return '';
  const mx = Math.max(...cs, 1e-12);
  const f = UI.tdVal === 'soles' ? fS : prom;
  return cs.map(q => `<td class="b num${q > 0 && q === mx ? ' pico' : ''}" style="background:${tono(q / mx, 22, 'transparent')}">${f(q)}</td>`).join('');
}
function totTD(x, factor, u) {
  const t = x.tot * factor;
  return UI.tdVal === 'soles' ? sol(t) : `${prom(t)}<span class="und">${esc(corta(u))}</span>`;
}
const coincide = s => !tdTxt || String(s).toLowerCase().includes(tdTxt);
const vendidos = x => !x ? '' : `${x % 1 === 0 ? n0(x) : dec(x, 2)} vendidos`;
// La receta de HOY: un plato cuya receta se editó dentro del rango se calcula
// con la nueva aunque se haya vendido antes (regla #560).
const marcaEditada = ed => !ed ? '' :
  `<span class="t-ed" title="La receta se editó el ${fCorta(ed)}: lo vendido antes de esa fecha se calcula con la receta de hoy.">receta editada ${fCorta(ed)}</span>`;
// Los porcionamientos de un corte (regla #609). Una venta no dice de qué
// porcionamiento salió su corte: lo que baja al insumo es el rendimiento de
// TODOS los de la ventana, así que se listan todos, con su N° del Almacén.
// z = [cuántos, cuántos del corte, desde, hasta, sólo respaldo, lista].
const porcsDe = (cod, prep) => ((D.porcs || {})[cod] || {})[prep];
const fDia = s => fCorta(s) + (fecha(s).a !== fecha(P.hasta).a ? ' ' + fecha(s).a : '');
const porcsMeta = z => !z ? '' : (z[0] === 1
  ? ` · porcionamiento N° ${esc(z[5][0][0])} del ${fDia(z[2])}`
  : ` · ${n0(z[0])} porcionamientos, ${fDia(z[2])} – ${fDia(z[3])}`);
// ── la cuenta de cada porcionamiento (regla #751) ──
// Lo que el árbol hizo con un corte, mes por mes: las unidades que usaron las
// ventas × lo que puso el insumo por unidad = lo que se usó del insumo. Y de
// dónde sale ese «por unidad»: lo que puso el insumo ÷ las unidades del corte
// de TODOS los porcionamientos de la ventana (otro insumo también puede
// hacerlo). rend_mes[insumo][corte][mes] = [rendimiento, puso, unidades,
// unidades de este insumo, su peso, cuántos, desde, hasta, fuente, alcance].
const REND = component.data.rendimiento === 'mes' ? 'mes' : '90';
const MERMAS = component.data.mermas || {};
const RM = D.rend_mes || {};
const PCX = D.porcs_corte || {};
const CONTEXTO = 'Lo que las ventas debieron usar: cada plato vendido, abierto por sus recetas hasta lo que se compra. Consumo teórico, a precios promedio de hoy; el real (inventarios + compras) está en Costos.';
const nombreCod = c => D.insumos[c] ? D.insumos[c][0] : (D.preps[c] ? D.preps[c][0] : ((D.nombres || {})[c] || c));
const kgU = v => !v ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: Math.abs(v) >= 10 ? 1 : (Math.abs(v) >= 1 ? 3 : 4) });
// Los dos lados de una división, con un decimal: redondeados a entero no cierran a la vista.
const q1 = v => !v ? '—' : (Math.abs(v) >= 10 ? dec(v, 1) : Number(v).toLocaleString('en-US', { maximumFractionDigits: 3 }));
const porcsVer = new Set();
function cuentaCorte(cod, b) {
  const rm = (RM[cod] || {})[b.prep];
  if (!rm) return null;
  const meses = [];
  P.meses.forEach((m, i) => {
    const q = b.m[i], c = rm[m];
    if (!c || !(q > 0)) return;
    const [r, entra, tot, saleE, pesoE, n, desde, hasta, fuente, alcance] = c;
    meses.push({ m, q, r, und: r > 0 ? q / r : 0, entra, tot, saleE, pesoE, n, desde, hasta, fuente, alcance });
  });
  if (!meses.length) return null;
  const ult = meses[meses.length - 1];
  const lista = ult.m === P.meses[NM - 1] ? (PCX[b.prep] || []) : [];
  return { cod, prep: b.prep, meses, ult, lista, und: suma(meses.map(x => x.und)), kg: suma(meses.map(x => x.q)) };
}
// La merma real sale del peso de los cortes que salieron de este insumo contra
// lo que puso; con la esperada, lo que habría pedido: kg × (1 − real) ÷ (1 − esperada).
function mermaDe(cuentas) {
  const xs = cuentas.flatMap(c => c.meses).filter(x => x.pesoE > 0 && x.entra > 0);
  const q = suma(xs.map(x => x.q));
  if (!q) return null;
  const util = suma(xs.map(x => x.q * x.pesoE / x.entra));
  const m = MERMAS[cuentas[0].cod], out = { q, real: 1 - util / q, esperada: m };
  if (m != null) { out.std = util / (1 - m / 100); out.dif = q - out.std; }
  return out;
}
const ventanaTxt = x => x.alcance === 'mes' ? `En ${fMes(x.m)}`
  : x.alcance === 'respaldo' ? `Sin porcionamientos en 90 días ni receta, en los ${n0(x.n)} más cercanos (${fMes(x.desde)} – ${fMes(x.hasta)})`
  : `En los 90 días que cierran ${fMes(x.m)} (${fDia(x.desde)} – ${fDia(x.hasta)})`;
function htmlMerma(cod, mm, nombre) {
  const [, u, pr] = D.insumos[cod];
  const val = MERMAS[cod] != null ? MERMAS[cod] : '';
  let lectura;
  if (mm.esperada == null) lectura = 'Pon tu merma esperada para ver cuánto se fue de más o de menos.';
  else {
    const d = mm.dif, cls = d > 0.005 ? 'mas' : (d < -0.005 ? 'menos' : '');
    lectura = `Con ${dec(mm.esperada, mm.esperada % 1 ? 1 : 0)} %, las ventas habrían pedido <b>${prom(mm.std)} ${esc(corta(u))}</b>: <b class="${cls}">${prom(Math.abs(d))} ${esc(corta(u))} ${d >= 0 ? 'más' : 'menos'}</b> de lo esperado, ≈ ${sol(Math.abs(d) * pr)}.`;
  }
  return `<div class="merma"><span><b>Merma real ${dec(100 * mm.real, 1)} %</b> en lo que llega por porcionamiento (${prom(mm.q)} ${esc(corta(u))}).</span>
    <label>Tu merma esperada de ${esc(nombre)} <input type="number" inputmode="decimal" data-merma="${esc(cod)}" value="${val}" min="0" max="89.9" step="0.5" placeholder="—" aria-label="Merma esperada de ${esc(nombre)} en %"> %</label>
    <span>${lectura}</span></div>`;
}
function filaCuenta(cu, z, cod, prep, ncol) {
  if (!cu) return filaPorcsVieja(z, cod, prep, ncol);
  const [nom, uIns] = D.insumos[cod], u = esc(corta(uIns)), uc = esc(corta(D.preps[prep] ? D.preps[prep][2] : ''));
  const x = cu.ult, mios = cu.lista.filter(p => p[2] === cod), otros = cu.lista.filter(p => p[2] !== cod);
  const nomOtros = [...new Set(otros.map(p => nombreCod(p[2])))];
  const lineas = cu.meses.map(m => `${fMes(m.m)}: ${prom(m.und)} ${uc} × ${kgU(m.r)} = ${prom(m.q)} ${u}`);
  const meses = lineas.length > 4 ? lineas.slice(-3).join(' · ') + ` · y ${lineas.length - 3} meses más (en el Excel)` : lineas.join(' · ');
  let origen = `<b>De dónde sale ${kgU(x.r)} ${u} por ${uc}.</b> ${ventanaTxt(x)} se hicieron <b>${q1(x.tot)} ${uc}</b> de este corte en <b>${n0(x.n)} porcionamiento${x.n === 1 ? '' : 's'}</b>.`;
  if (cu.lista.length) origen += ` ${mios.length === 1 ? 'El que salió' : `Los ${mios.length} que salieron`} de ${esc(nom)} le pusieron <b>${q1(x.entra)} ${u}</b>`;
  else origen += ` ${esc(nom)} le puso <b>${q1(x.entra)} ${u}</b>`;
  origen += `: <span class="mini-eq num">${q1(x.entra)} ÷ ${q1(x.tot)} = ${kgU(x.r)}</span>.`;
  if (otros.length) origen += ` ${otros.length === 1 ? 'El otro salió' : `Los otros ${otros.length} salieron`} de ${esc(nomOtros.join(' y '))}: sus cortes cuentan en el total.`;
  let ult = '';
  if (mios.length) {
    const rs = mios.map(p => p[4] / p[5]), p0 = mios[0];
    ult = `<p class="ult">El último de ${esc(nom)}, del ${fDia(p0[1])} (N° ${esc(p0[0])}), dio <b>${kgU(p0[4] / p0[5])} ${u}</b> por ${uc}.${mios.length > 1 ? ` Es un dato, no la base: en la ventana van de ${kgU(Math.min(...rs))} a ${kgU(Math.max(...rs))}.` : ''}</p>`;
  }
  const mm = mermaDe([cu]);
  const k = cod + '|' + prep, ver = porcsVer.has(k);
  let tabla = '';
  if (ver && cu.lista.length) {
    const prm = suma(mios.map(p => p[4])) / (suma(mios.map(p => p[5])) || 1);
    const mx = Math.max(...mios.map(p => p[4] / p[5]), 1e-9);
    tabla = `<div class="porcs-wrap"><table class="porcs-t"><thead><tr><th>N° del Almacén</th><th>Fecha</th><th>Desde</th><th class="r">Se porcionaron</th><th class="r">A este corte</th><th class="r">Cortes</th><th class="r">${u} por ${uc}</th></tr></thead><tbody>
      ${cu.lista.map(p => { const mio = p[2] === cod, r = p[4] / p[5], lejos = mio && Math.abs(r - prm) > 0.25 * prm;
        return `<tr class="${mio ? '' : 'otro'}"><td class="num">${esc(p[0])}</td><td>${fDia(p[1])}</td><td>${esc(nombreCod(p[2]))}</td><td class="r num">${prom(p[3])}</td><td class="r num">${mio ? prom(p[4]) : '—'}</td><td class="r num">${prom(p[5])}</td>
          <td class="r num">${mio ? `<span class="kgu${lejos ? ' lejos' : ''}"><i style="width:${Math.round(40 * r / mx)}px"></i>${kgU(r)}</span>` : '—'}</td></tr>`; }).join('')}
      <tr class="tot"><td colspan="4">Lo que entra en la cuenta</td><td class="r num">${q1(x.entra)}</td><td class="r num">${q1(x.tot)}</td><td class="r num">${kgU(x.r)}</td></tr></tbody></table></div>
      <p class="nota">«A este corte» es lo que le tocó por su peso, la regla del Almacén. ${otros.length ? 'Los cortes que salieron de otro insumo cuentan en el total. ' : ''}En ámbar, los que se apartan más de 25 % del promedio de ${esc(nom)}.</p>`;
  }
  return `<tr class="lvp"><td colspan="${ncol}"><div class="porcs cuenta">
    <div class="eq"><span class="term"><b>${prom(cu.und)} ${uc}</b><small>de ${esc(prepNombre(prep))} usadas por las ventas</small></span><span class="op">×</span>
      <span class="term"><b>${kgU(cu.kg / cu.und)} ${u}</b><small>de ${esc(nom)} por ${uc}</small></span><span class="op">=</span>
      <span class="term res"><b>${prom(cu.kg)} ${u}</b><small>de ${esc(nom)}</small></span></div>
    <div class="meses-eq num">${meses}</div>
    <p class="origen">${origen}</p>${ult}
    ${mm ? htmlMerma(cod, mm, nom) : ''}
    ${cu.lista.length ? `<button type="button" class="ver-porcs" data-porcs="${esc(k)}" aria-expanded="${ver}">${ver ? 'Ocultar' : 'Ver'} los ${cu.lista.length} porcionamientos ${ver ? '▴' : '▾'}</button>` : ''}${tabla}
  </div></td></tr>`;
}
// Sin la cuenta (una caché anterior a la versión 4): los N° del Almacén.
function filaPorcsVieja(z, cod, prep, ncol) {
  const [n, nCorte, desde, , resp, l] = z;
  const u = esc(corta(D.insumos[cod][1])), uc = esc(corta(D.preps[prep] ? D.preps[prep][2] : ''));
  const nom = esc(D.insumos[cod][0]);
  const de = resp ? `no hubo en los 90 días y el corte no tiene receta: ${n === 1 ? 'el más cercano' : 'los más cercanos'}`
                  : `los de los 90 días que cierran ${NM > 1 ? 'cada' : 'el'} mes`;
  const otros = nCorte > n
    ? ` Otros ${n0(nCorte - n)} hicieron este corte desde otros insumos: entran en la cuenta para repartirlo.` : '';
  const chips = l.map(([po, f, cant, entra, sale]) =>
    `<span class="pc num" title="N° ${esc(po)} del ${fDia(f)}: se porcionaron ${prom(cant)} ${u} de ${nom}; a este corte le tocaron ${prom(entra)} ${u} por ${sale % 1 === 0 ? n0(sale) : prom(sale)} ${uc}.">${esc(po)}<small>${fDia(f)}</small></span>`).join('');
  const mas = n > l.length ? `<span>y ${n0(n - l.length)} más, desde el ${fDia(desde)}</span>` : '';
  return `<tr class="lvp"><td colspan="${ncol}"><div class="porcs"><span class="porcs-tit">El rendimiento sale de <b>${n0(n)} porcionamiento${n === 1 ? '' : 's'}</b> (${de}).${otros} N° del Almacén y fecha:</span>${chips}${mas}</div></td></tr>`;
}
function pintarDinamica(foco) {
  tdCabeza();
  let lista = A.lista;
  const fams = [...new Set(lista.map(a => D.insumos[a.cod][3]))].filter(Boolean).sort();
  if (tdFam !== 'Todas' && !fams.includes(tdFam)) tdFam = 'Todas';
  document.getElementById('td-fams').innerHTML = ['Todas', ...fams].map(f =>
    `<button class="chipf" type="button" aria-pressed="${f === tdFam}" data-f="${esc(f)}">${esc(f === 'Todas' ? f : cap(f))}</button>`).join('');
  if (tdFam !== 'Todas') lista = lista.filter(a => D.insumos[a.cod][3] === tdFam);
  const filasH = [], visibles = [];
  for (const a of lista) {
    const [nom, u, pr, fam, sub] = D.insumos[a.cod];
    const f = UI.tdVal === 'soles' ? pr : 1;
    const preps = [...a.preps.values()].sort((x, y) => y.tot - x.tot);
    let hijosVis = preps, forzado = false;
    if (tdTxt && !coincide(nom)) {
      hijosVis = preps.filter(b => coincide(prepNombre(b.prep)) || [...b.platos.values()].some(c => coincide(PLATOS[c.pid][0])));
      if (!hijosVis.length) continue;
      forzado = true;
    }
    visibles.push(a);
    const k0 = 'i:' + a.cod, ab0 = forzado || tdAbiertos.has(k0);
    filasH.push(`<tr class="lv0${ab0 ? ' abierto' : ''}" data-k="${esc(k0)}" tabindex="0" aria-expanded="${ab0}">
      <td class="c-nom"><div class="fila"><span class="flecha">${CHEV}</span><span class="txt"><span class="nm">${esc(nom)}</span><span class="meta">${esc(cap(fam))} · ${esc(sub || '')} · ${preps.length} preparaci${preps.length === 1 ? 'ón' : 'ones'}</span></span></div></td>
      <td class="c-tot num">${totTD(a, f, u)}</td>${celdasTD(a, f)}</tr>`);
    if (!ab0) continue;
    for (const b of hijosVis) {
      const k1 = 'p:' + a.cod + '|' + b.prep;
      let platos = [...b.platos.values()].sort((x, y) => y.tot - x.tot);
      let forz1 = false;
      if (forzado && !coincide(prepNombre(b.prep))) { platos = platos.filter(c => coincide(PLATOS[c.pid][0])); forz1 = true; }
      const ab1 = forz1 || tdAbiertos.has(k1);
      const z = porcsDe(a.cod, b.prep);
      filasH.push(`<tr class="lv1${ab1 ? ' abierto' : ''}" data-k="${esc(k1)}" tabindex="0" aria-expanded="${ab1}">
        <td class="c-nom"><div class="fila"><span class="flecha">${CHEV}</span><span class="txt"><span class="nm">${prepEtiqueta(b.prep)}</span><span class="meta num">${b.platos.size} plato${b.platos.size === 1 ? '' : 's'}${porcsMeta(z)}</span></span></div></td>
        <td class="c-tot num">${totTD(b, f, u)}</td>${celdasTD(b, f)}</tr>`);
      if (!ab1) continue;
      const cu = cuentaCorte(a.cod, b);
      if (cu || z) filasH.push(filaCuenta(cu, z, a.cod, b.prep, 2 + cubetas(b).length));
      for (const c of platos) {
        const [pn, vi, vend, ed] = PLATOS[c.pid];
        const enReceta = c.n1.size ? `<span class="meta">en la receta: ${esc([...c.n1].map(prepNombre).join(' · '))}</span>` : '';
        filasH.push(`<tr class="lv2">
          <td class="c-nom"><div class="fila"><span class="txt"><span class="nm">${esc(pn)}</span>${vi ? '<span class="t-vi">venta interna</span>' : ''}${marcaEditada(ed)}<span class="meta num">${vendidos(vend)}</span>${enReceta}</span></div></td>
          <td class="c-tot num">${totTD(c, f, u)}</td>${celdasTD(c, f)}</tr>`);
      }
    }
  }
  if (UI.tdVal === 'soles') {
    const t = vec();
    for (const a of visibles) {
      const p = D.insumos[a.cod][2];
      for (let i = 0; i < NF; i++) t.v[i] += a.v[i] * p;
      for (let i = 0; i < NM; i++) t.m[i] += a.m[i] * p;
      for (let k = 0; k < 7; k++) t.ds[k] += a.ds[k] * p;
      t.t[0] += a.t[0] * p; t.t[1] += a.t[1] * p; t.tot += a.tot * p;
    }
    filasH.unshift(`<tr class="lvt"><td class="c-nom">Total${tdTxt || tdFam !== 'Todas' ? ' de lo filtrado' : ''} · ${visibles.length} insumos</td>
      <td class="c-tot num">${sol(t.tot)}</td>${celdasTD(t, 1)}</tr>`);
  }
  const tb = document.getElementById('td-filas');
  const hasta=foco?filasH.findIndex(h=>h.includes('data-k="'+esc(foco)+'"'))+1:0;
  porTandas(tb,filasH,x=>x,`<tr><td colspan="2">Nada coincide con «${esc(tdTxt)}».</td></tr>`,hasta,!!foco);
  recordarFiltros();
  if (foco) { const tr = tb.querySelector(`tr[data-k="${CSS.escape(foco)}"]`); if (tr) tr.focus({ preventScroll: true }); }
  const expl = {
    total: 'Total del período.',
    semana: 'Total de cada semana' + (Array.from({ length: NS }, (_, i) => semParcial(i)).some(Boolean) ? '; * semana incompleta en el rango.' : '.'),
    dia: 'Total de cada día. Desliza a la derecha: el nombre y el total quedan fijos.',
    mes: 'Total de cada mes del rango.',
    dsem: `Promedio por día: lo de todos los lunes del rango entre ${P.n_dia[0]}, lo de los sábados entre ${P.n_dia[5]}.`,
    turno: `Almuerzo: platos pedidos antes de las 17 h, con la hora de cada plato${D.resumen.hora_de_mesa ? ' (hoy, la de la mesa: el parquet no trae la del plato)' : ''}.`,
  }[UI.tdCols];
  document.getElementById('td-pie').textContent = `${visibles.length} de ${A.lista.length} insumos${UI.vi ? '' : ' (sin venta interna)'}. ${expl}` +
    (UI.tdVal === 'soles' ? ' Soles al precio promedio de hoy.' : ' Cada fila va en la unidad de su insumo, la del kardex.');
}
const pintarSegTD = () => {
  document.querySelectorAll('#td-cols button').forEach(b => b.setAttribute('aria-pressed', b.dataset.c === UI.tdCols));
  document.querySelectorAll('#td-val button').forEach(b => b.setAttribute('aria-pressed', b.dataset.x === UI.tdVal));
};
document.getElementById('td-cols').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; UI.tdCols = b.dataset.c; guardar(); pintarSegTD(); pintarDinamica(); });
document.getElementById('td-val').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; UI.tdVal = b.dataset.x; guardar(); pintarSegTD(); pintarDinamica(); });
document.getElementById('td-fams').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; tdFam = b.dataset.f; pintarDinamica(); });
document.getElementById('td-buscar').addEventListener('input', e => { tdTxt = e.target.value.trim().toLowerCase(); pintarDinamica(); });
document.getElementById('td-plegar').addEventListener('click', () => { tdAbiertos.clear(); pintarDinamica(); });
const alternar = tr => { const k = tr.dataset.k; if (!k) return; tdAbiertos.has(k) ? tdAbiertos.delete(k) : tdAbiertos.add(k); pintarDinamica(k); };
document.getElementById('td-filas').addEventListener('click', e => { const tr = e.target.closest('tr[data-k]'); if (tr) alternar(tr); });
document.getElementById('td-filas').addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const tr = e.target.closest('tr[data-k]'); if (tr) { e.preventDefault(); alternar(tr); }
});

// ═══ RESUMEN: la tabla de insumos y la ficha ═══
const modos = document.getElementById('modos');
const pintarModos = () => modos.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.m === UI.modo));
modos.addEventListener('click', e => { const b = e.target.closest('button'); if (!b || b.dataset.m === UI.modo) return; UI.modo = b.dataset.m; guardar(); pintarModos(); pintarCabeza(); pintarFilas(); pintarDetalle(); });
let famSel=texto(UI.famSel)||'Todas',txt=texto(UI.txt);
document.getElementById('buscar').value=txt;
const famBox = document.getElementById('familias');
function pintarFams() {
  const fams = [...new Set(A.lista.map(a => D.insumos[a.cod][3]))].filter(Boolean).sort();
  if (famSel !== 'Todas' && !fams.includes(famSel)) famSel = 'Todas';
  famBox.innerHTML = ['Todas', ...fams].map(f =>
    `<button class="chipf" type="button" aria-pressed="${f === famSel}" data-f="${esc(f)}">${esc(f === 'Todas' ? f : cap(f))}</button>`).join('');
}
famBox.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; famSel = b.dataset.f; pintarFams(); pintarFilas(); });
document.getElementById('buscar').addEventListener('input', e => { txt = e.target.value.trim().toLowerCase(); pintarFilas(); });
// Con más de 16 semanas (un rango de meses) la tira y la ficha van MES a mes:
// 53 barras no entran en 500px y sus números se pisan.
const LARGO = NS > 16;
const semanasDe = a => { if (LARGO) return Array.from(a.m); const s = new Array(NS).fill(0); for (let i = 0; i < NF; i++) s[semIdx[i]] += a.v[i]; return s; };
const tituloSerie = i => LARGO ? fMes(P.meses[i]) : fCorta(semTitulo(i)) + (semParcial(i) ? '*' : '');
if (LARGO) document.querySelector('#modos button[data-m="semanas"]').textContent = 'Mes';
const diasDe = a => Array.from(a.ds, (q, k) => P.n_dia[k] ? q / P.n_dia[k] : 0);
function horasDe(a) {
  const h = D.horas_ins[a.cod] || [[], []];
  return Array.from({ length: NH }, (_, j) => ((h[0][j] || 0) + (UI.vi ? (h[1][j] || 0) : 0)) / P.n_dias);
}
function mapaDe(a) {
  const m = D.mapa_ins[a.cod] || [[], []];
  const out = Array.from({ length: 7 }, () => new Array(NH).fill(0));
  for (const [d, j, q] of m[0]) out[d][j] += q;
  if (UI.vi) for (const [d, j, q] of m[1]) out[d][j] += q;
  return out.map((fila, d) => fila.map(q => P.n_dia[d] ? q / P.n_dia[d] : 0));
}
const turnosDe = vals => { let al = 0, ce = 0; vals.forEach((v, j) => { if (esAlmuerzo(D.horas[j])) al += v; else ce += v; }); return { al, ce }; };
const cabeza = document.getElementById('cabeza');
function pintarCabeza() {
  const base = `<th class="rk">#</th><th>Insumo</th>` + (UI.modo === 'semanas'
    ? `<th class="r">Cantidad</th><th class="r">Costo</th>`
    : `<th class="r">Cantidad<div class="th-sub">costo</div></th>`);
  const eje = `<div class="eje" aria-hidden="true" style="--nh:${NH}">${D.horas.map((h, j) => `<span>${j % 4 === 0 ? h : ''}</span>`).join('')}</div>`;
  cabeza.innerHTML = '<tr>' + base + ({
    semanas: `<th class="r">% del total</th><th>${LARGO ? 'Por mes' : 'Por semana'}</th>`,
    dias: DIAS.map(d => `<th class="dia">${d}</th>`).join(''),
    horas: `<th class="r">Almuerzo</th><th class="r">Cena</th><th>Por hora${eje}</th>`,
  })[UI.modo] + '</tr>';
}
const marcaVI = a => (UI.vi && a.tot && a.vi / a.tot >= 0.25) ? ` · <span class="vi">${pct0(a.vi, a.tot)} venta interna</span>` : '';
function celdasModo(a, costoTot) {
  const u = D.insumos[a.cod][1];
  if (UI.modo === 'semanas') {
    const s = semanasDe(a), mx = Math.max(...s, 1e-9);
    return `<td class="r num">${pct(a.costo, costoTot)}</td><td><span class="spark" aria-label="consumo por semana">${s.map(v => `<span style="height:${Math.max(2, 22 * v / mx)}px"></span>`).join('')}</span></td>`;
  }
  if (UI.modo === 'dias') {
    const d = diasDe(a), mx = Math.max(...d, 1e-9);
    return d.map((v, i) => `<td class="dia num${v > 0 && v === mx ? ' pico' : ''}" style="background:${tono(v / mx, 24, 'transparent')}" title="${DIAS_L[i]}: ${prom(v)} ${esc(corta(u))} por día">${prom(v)}</td>`).join('');
  }
  const h = horasDe(a), { al, ce } = turnosDe(h), mx = Math.max(...h, 1e-9);
  return `<td class="r num">${prom(al)}</td><td class="r num">${prom(ce)}</td>
    <td><span class="tira" style="--nh:${NH}" aria-label="consumo por hora">${h.map((v, j) => `<span style="background:${tono(v / mx, 100, 'var(--linea)')}" title="${D.horas[j]} h: ${prom(v)} ${esc(corta(u))} por día"></span>`).join('')}</span></td>`;
}
const filas = document.getElementById('filas');
function pintarFilas() {
  const costoTot = suma(A.lista.map(a => a.costo));
  const vis = A.lista.filter(a => (famSel === 'Todas' || D.insumos[a.cod][3] === famSel) && (!txt || D.insumos[a.cod][0].toLowerCase().includes(txt)));
  if (!UI.sel || !A.ins.has(UI.sel)) UI.sel = (vis[0] || A.lista[0] || {}).cod || null;
  porTandas(filas,vis,a => {
    const [nom, u, , fam, sub] = D.insumos[a.cod];
    const rk = A.lista.indexOf(a) + 1;
    const cant = `${prom(a.tot)}<span class="und">${esc(corta(u))}</span>`;
    return `<tr tabindex="0" data-cod="${esc(a.cod)}" aria-selected="${a.cod === UI.sel}">
      <td class="rk num">${rk}</td>
      <td><div class="nom">${esc(nom)}</div><div class="fam">${esc(cap(fam))} · ${esc(sub || '')}${marcaVI(a)}</div></td>
      ${UI.modo === 'semanas' ? `<td class="r num">${cant}</td><td class="r num">${sol(a.costo)}</td>` : `<td class="r num">${cant}<div class="costo-sub">${sol(a.costo)}</div></td>`}
      ${celdasModo(a, costoTot)}
    </tr>`;
  },'<tr><td colspan="12">Nada coincide con este filtro.</td></tr>');
  avisoFicha(vis);recordarFiltros();
  const s = suma(vis.map(a => a.costo));
  document.getElementById('pie').textContent = `${vis.length} de ${A.lista.length} insumos · suman ${sol(s)} (${pct(s, costoTot)} del costo).` + ({
    semanas: '',
    dias: ` Cada día es un promedio, en la unidad de la fila: lo de los ${P.n_dia[0]} lunes entre ${P.n_dia[0]}, lo de los ${P.n_dia[5]} sábados entre ${P.n_dia[5]}.`,
    horas: ` Almuerzo y cena: promedio por día; el almuerzo son los platos pedidos antes de las 17 h.`,
  })[UI.modo];
}
filas.addEventListener('click', e => { const tr = e.target.closest('tr'); if (tr) elegir(tr.dataset.cod); });
filas.addEventListener('keydown', e => { if (e.key === 'Enter') { const tr = e.target.closest('tr'); if (tr) elegir(tr.dataset.cod); } });
function elegir(cod) { if(!A.ins.has(cod))return; UI.sel = cod; guardar(); filas.querySelectorAll('tr').forEach(tr => tr.setAttribute('aria-selected', tr.dataset.cod === cod)); pintarDetalle(); avisoFicha(resumenVisible()); }
function barras(items, color, fmt) {
  const mx = Math.max(...items.map(i => i[1]), 1e-9);
  return items.map(([lbl, v, col]) => `<div class="fila-bar"><span class="lbl" title="${esc(lbl)}">${esc(lbl)}</span><span class="val num">${fmt(v)}</span>
    <div class="bg"><span style="width:${100 * v / mx}%;background:${col || color}"></span></div></div>`).join('');
}
function mapaHTML(a) {
  const u = corta(D.insumos[a.cod][1]), m = mapaDe(a), todo = m.flat(), mx = Math.max(...todo, 1e-9);
  const k = todo.indexOf(mx), di = Math.floor(k / NH), hj = k % NH;
  const cab = '<span></span>' + D.horas.map(h => `<span class="mh">${h}</span>`).join('');
  const cuerpo = m.map((fila, i) => `<span class="md">${DIAS[i]}</span>` + fila.map((v, j) =>
    `<span class="mc" style="background:${tono(v / mx, 100, 'var(--linea)')}" title="${DIAS_L[i]} ${D.horas[j]} h: ${prom(v)} ${esc(u)} en promedio"></span>`).join('')).join('');
  return `<div class="mapa num" style="grid-template-columns: 30px repeat(${NH}, minmax(0, 1fr))">${cab}${cuerpo}</div>
    <p class="nota num">Día × hora del plato, en promedio por ese día de la semana. Lo más fuerte: el <b>${DIAS_L[di]} a las ${D.horas[hj]} h</b>, ${prom(mx)} ${esc(u)}.</p>`;
}
function seccionCuando(a) {
  const u = D.insumos[a.cod][1];
  if (UI.modo === 'semanas') {
    const s = semanasDe(a), mx = Math.max(...s, 1e-9);
    const hayParcial = !LARGO && s.some((_, i) => semParcial(i));
    return `<div class="det-sec"><h3>${LARGO ? 'Mes a mes' : 'Semana a semana'}<small>en ${esc(corta(u))}</small></h3>
      <div class="semanas" style="--n:${s.length}">${s.map((v, i) => `<div class="sem"><span class="v num">${s.length > 8 ? '' : prom(v)}</span><div class="col" style="height:${Math.max(2, 70 * v / mx)}px;opacity:.85" title="${esc(tituloSerie(i))}: ${prom(v)}"></div><span>${s.length > 8 && i % 2 ? '' : tituloSerie(i)}</span></div>`).join('')}</div>
      ${hayParcial ? '<p class="nota">* semana incompleta en el rango.</p>' : ''}</div>`;
  }
  if (UI.modo === 'dias') {
    const d = diasDe(a), mx = Math.max(...d, 1e-9), pos = d.filter((_, k) => P.n_dia[k]);
    const mn = Math.min(...pos), ip = d.indexOf(mx), im = d.indexOf(mn);
    const veces = mn > 0 ? `El <b>${DIAS_L[ip]}</b> se usa ${dec(mx / mn, 1)} veces lo de un ${DIAS_L[im]}. ` : '';
    return `<div class="det-sec"><h3>Por día de la semana<small>promedio por día, en ${esc(corta(u))}</small></h3>
      <div class="semanas" style="--n:7">${d.map((v, i) => `<div class="sem${i === ip ? ' pico' : ''}"><span class="v num">${prom(v)}</span><div class="col" style="height:${Math.max(2, 70 * v / mx)}px"></div><span>${DIAS[i]}</span></div>`).join('')}</div>
      <p class="nota num">${veces}Lo de los ${P.n_dia[0]} lunes entre ${P.n_dia[0]}, lo de los ${P.n_dia[5]} sábados entre ${P.n_dia[5]}.</p>${mapaHTML(a)}</div>`;
  }
  const h = horasDe(a), mx = Math.max(...h, 1e-9), ip = h.indexOf(mx), { al, ce } = turnosDe(h);
  return `<div class="det-sec"><h3>Por hora del plato<small>promedio por día, en ${esc(corta(u))}</small></h3>
    <div class="semanas" style="--n:${NH};gap:3px">${h.map((v, j) => `<div class="sem${j === ip ? ' pico' : ''}" style="font-size:10.5px"><span class="v num">${v >= 0.5 * mx ? prom(v) : ''}</span><div class="col" style="height:${Math.max(2, 70 * v / mx)}px" title="${D.horas[j]} h: ${prom(v)}"></div><span>${D.horas[j]}</span></div>`).join('')}</div>
    <div class="turnos">
      <div><div class="eyebrow">Almuerzo · antes de las 17 h</div><div class="grande num">${prom(al)} <span class="und">${esc(corta(u))} por día</span></div><div class="sub num">${pct0(al, al + ce)} del consumo</div></div>
      <div><div class="eyebrow">Cena · desde las 17 h</div><div class="grande num">${prom(ce)} <span class="und">${esc(corta(u))} por día</span></div><div class="sub num">${pct0(ce, al + ce)} del consumo</div></div>
    </div>${mapaHTML(a)}</div>`;
}
function pintarDetalle() {
  const det = document.getElementById('detalle');
  const a = A.ins.get(UI.sel);
  if (!a) { det.innerHTML = '<div class="det-sec"><p class="nota">Ningún insumo en el período.</p></div>'; return; }
  const [nom, u, pr, fam, sub, factor, us] = D.insumos[a.cod];
  const costoTot = suma(A.lista.map(x => x.costo));
  const equivalente = (factor && factor !== 1 && us) ? `<div class="sub num">= ${n0(a.tot * factor)} ${esc(us)} en las recetas</div>` : '';
  const cams = [...a.cam.entries()].sort((x, y) => y[1] - x[1]);
  const totCam = suma(cams.map(x => x[1]));
  const platos = [...a.pl.entries()].sort((x, y) => y[1] - x[1]).slice(0, 6);
  const nombresVI = [...a.pl.keys()].filter(p => PLATOS[p][1]).map(p => PLATOS[p][0]).slice(0, 2);
  const avisoVI = (UI.vi && a.tot && a.vi / a.tot >= 0.25)
    ? `<div class="det-sec aviso-vi"><p><b>${pct0(a.vi, a.tot)} sale de venta interna</b> (${esc(nombresVI.join(' y '))}): se produce por tanda, así que su día y su hora son los de la producción, no los del servicio. Apaga «Venta interna» para ver el patrón del salón.</p></div>` : '';
  let rend = '';
  const cortes = [...a.porc.entries()].sort((x, y) => y[1] - x[1]);
  if (cortes.length) {
    const cuentas = [];
    const items = cortes.map(([cx, q]) => {
      const b = a.preps.get(cx), cu = b ? cuentaCorte(a.cod, b) : null;
      const uc = D.preps[cx] ? D.preps[cx][2] : '';
      const revisar = D.revisar.includes(cx) ? '<span class="tag rev" title="Al corte se le asignó menos insumo del que pesa: pasa con los subproductos (grasa, retazos, carcasa) a los que la cocina les anota poco peso para cargarles poco costo.">Revisar: pesa más de lo que se le asignó</span>' : '';
      if (cu) {
        cuentas.push(cu);
        const x = cu.ult;
        const tag = x.alcance === 'respaldo' ? '<span class="tag resp">Respaldo</span>' : (x.alcance === 'mes' ? '<span class="tag ok">Último mes</span>' : '<span class="tag ok">Últimos 90 días</span>');
        return `<div class="rend-item"><div class="rend-top"><b>${esc(prepNombre(cx))}</b><span class="num">${prom(q)} ${esc(corta(u))}</span></div>
          <div class="rend-cuenta num">${prom(cu.und)} ${esc(corta(uc))} × ${kgU(cu.kg / cu.und)} ${esc(corta(u))} = ${prom(cu.kg)} ${esc(corta(u))}</div>
          <div class="rend-meta"><span class="num">${kgU(x.r)} = ${q1(x.entra)} ${esc(corta(u))} ÷ ${q1(x.tot)} ${esc(corta(uc))}</span>${tag}<span class="num">${n0(x.n)} porc. · ${x.alcance === 'respaldo' ? `${fMes(x.desde)} – ${fMes(x.hasta)}` : `${fCorta(x.desde)} – ${fCorta(x.hasta)}`}</span>${revisar}</div></div>`;
      }
      const r = (D.rend[a.cod] || {})[cx];
      if (!r) return `<div class="rend-item"><div class="rend-top"><b>${esc(prepNombre(cx))}</b><span class="num">${prom(q)} ${esc(corta(u))}</span></div></div>`;
      const [rv, fuente, n, desde, hasta] = r;
      const base = fuente === 'ventana'
        ? `<span class="tag ok">Últimos 90 días</span><span class="num">${n} cortes · ${fCorta(desde)} – ${fCorta(hasta)}</span>`
        : `<span class="tag resp">Respaldo</span><span class="num">sin porcionamientos en 90 días ni receta: los ${n} más cercanos (${fMes(desde)} – ${fMes(hasta)})</span>`;
      return `<div class="rend-item"><div class="rend-top"><b>${esc(prepNombre(cx))}</b><span class="num">${prom(q)} ${esc(corta(u))}</span></div>
        <div class="rend-meta"><span class="num">${rv.toLocaleString('en-US', { maximumFractionDigits: 4 })} ${esc(corta(u))} por ${esc(corta(uc))}</span>${base}${revisar}</div></div>`;
    });
    const mm = cuentas.length ? mermaDe(cuentas) : null;
    rend = `<div class="det-sec"><h3>Cómo se calculó el porcionamiento</h3>
      <p class="nota" style="margin:0 0 10px">Cada corte: las unidades que usaron las ventas × lo que puso ${esc(nom)} por unidad. ${REND === 'mes' ? 'Con los porcionamientos de cada mes («Último mes»); si en el mes no hubo, los de 90 días.' : 'Con los porcionamientos de los 90 días que cierran cada mes.'}</p>
      <div class="rend">${items.join('')}</div>${mm ? htmlMerma(a.cod, mm, nom) : ''}</div>`;
  }
  let real = '';
  const viaPorc = suma(cortes.map(x => x[1]));
  const pr_real = D.porcionado[a.cod];
  if (pr_real && viaPorc) {
    const dif = pr_real - viaPorc;
    const parte = viaPorc < 0.995 * a.tot ? ' (lo que llega por porcionamiento)' : '';
    real = `<div class="det-sec"><h3>Contra lo que se porcionó de verdad</h3>
      <div class="real"><div><div class="eyebrow">Explican las ventas${parte}</div><div class="grande num">${prom(viaPorc)} <span class="und">${esc(corta(u))}</span></div></div>
      <div><div class="eyebrow">Se porcionaron</div><div class="grande num">${prom(pr_real)} <span class="und">${esc(corta(u))}</span></div></div></div>
      <p class="nota num">${dif >= 0 ? 'Se porcionaron' : 'Las ventas explican'} ${prom(Math.abs(dif))} ${esc(corta(u))} más (${pct(Math.abs(dif), viaPorc)}). Se porciona por tandas: en un mes no tiene por qué cerrar.</p></div>`;
  }
  det.innerHTML = `
    <div class="det-cab">
      <div class="eyebrow">${esc(fam)} › ${esc(sub || '')}</div>
      <h2>${esc(nom)}</h2>
      <div class="det-cifras">
        <div><div class="grande num">${prom(a.tot)} <span class="und" style="font-size:14px">${esc(corta(u))}</span></div>${equivalente}</div>
        <div class="num" style="text-align:right"><div style="font-weight:600;font-size:16px">${sol(a.costo)}</div><div class="sub">${pct(a.costo, costoTot)} del costo del período</div></div>
      </div>
    </div>
    ${avisoVI}
    <div class="det-sec"><h3>Cómo llega al plato</h3>
      <div class="barra-llega" style="margin:0 0 10px">${cams.map(([k, v]) => `<span style="width:${100 * v / (totCam || 1)}%;background:${GRUPOS[k].col}"></span>`).join('')}</div>
      ${barras(cams.map(([k, v]) => [GRUPOS[k].txt, v, GRUPOS[k].col]), null, v => `${prom(v)} ${esc(corta(u))} · ${pct(v, totCam)}`)}
    </div>
    <div class="det-sec"><h3>Platos que más lo usan</h3>
      ${barras(platos.map(([p, v]) => [PLATOS[p][0], v]), 'var(--acento)', v => `${prom(v)} ${esc(corta(u))}`)}
      ${notaEditadas(platos.map(([p]) => p))}
    </div>
    ${seccionCuando(a)}${rend}${real}${contraCompras(a)}`;
}

function notaEditadas(pids) {
  const ed = pids.filter(p => PLATOS[p][3]).map(p => `${PLATOS[p][0]} (${fCorta(PLATOS[p][3])})`);
  if (!ed.length) return '';
  return `<p class="nota-ed">Receta editada en el período: ${esc(ed.join(', '))}. Lo vendido antes de esa fecha se calcula con la receta de hoy.</p>`;
}
function contraCompras(a) {
  const [, u, , fam] = D.insumos[a.cod];
  if (!D.compras_familias.length) return '';
  const c = D.compras[a.cod];
  const u_ = esc(corta(u));
  const titulo = `<h3>Contra lo que se compró<small>del ${fCorta(P.desde)} al ${fCorta(P.hasta)}, por la fecha del documento</small></h3>`;
  if (!c) {
    if (!FAM_C.has(String(fam).toUpperCase())) return '';
    return `<div class="det-sec">${titulo}<p class="nota" style="margin:0">No se compró en el período: lo que se usó salió del stock, o se compra con otro código.</p></div>`;
  }
  const [qc, sc, docs] = c, dif = qc - a.tot;
  const txt = Math.abs(dif) < 1e-9 ? 'Lo mismo que explican las ventas.'
    : (dif > 0 ? `Se compró ${prom(dif)} ${u_} más de lo que explican las ventas (${pct(dif, a.tot)}).`
               : `Las ventas explican ${prom(-dif)} ${u_} más de lo que se compró (${pct(-dif, a.tot)}): salió del stock.`);
  return `<div class="det-sec">${titulo}
    <div class="real"><div><div class="eyebrow">Explican las ventas</div><div class="grande num">${prom(a.tot)} <span class="und">${u_}</span></div></div>
    <div><div class="eyebrow">Se compraron</div><div class="grande num">${prom(qc)} <span class="und">${u_}</span></div><div class="sub num">${sol(sc)} en ${docs} documento${docs === 1 ? '' : 's'}</div></div></div>
    <p class="nota num">${txt} Comprar no es usar: el stock sube y baja entre compras, y hay usos que no pasan por una receta (aceite de freír, comida del personal, pruebas).${UI.vi ? '' : ' Con la venta interna apagada, lo que se compró para ella queda del lado de lo comprado.'}</p></div>`;
}

// ═══ CONTRA COMPRAS: todo lo comprado del rango, al lado de lo que explican las ventas ═══
const FAM_C = new Set((D.compras_familias || []).map(f => String(f).toUpperCase()));
const FAM_DEFECTO = ['ALIMENTOS', 'BEBIDAS CON ALCOHOL', 'BEBIDAS SIN ALCOHOL', 'VINOS Y ESPUMANTES'];
const famsTexto = () => {
  const f = [...FAM_C].sort();
  return f.length === FAM_DEFECTO.length && f.every((x, i) => x === FAM_DEFECTO[i])
    ? 'alimentos y bebidas' : f.map(x => cap(x).toLowerCase()).join(', ');
};
// «Diferencia grande»: más del 25 % de lo que explican las ventas Y más de
// S/ 100. Con el 25 % solo, un mes de septiembre de 2026 marcaba 305 de 417
// insumos (lo chico se compra cada tanto y casi nunca cierra en un mes); con
// los dos, 93, y arriba lo que importa: cachema, bife ancho, naranja, papa.
const DIF_MIN_SOLES = 100;
const FILTROS_C = [['todo', 'Todo'], ['sin', 'Ninguna venta los usó'], ['dif', 'Diferencia grande']];
let ccTxt=texto(UI.ccTxt),ccFiltro=FILTROS_C.some(f=>f[0]===UI.ccFiltro)?UI.ccFiltro:'todo';
document.getElementById('cc-buscar').value=ccTxt;
function filasCompras() {
  const out = [], vistos = new Set();
  for (const a of A.lista) {
    const [nom, u, , fam, sub] = D.insumos[a.cod];
    if (!FAM_C.has(String(fam).toUpperCase())) continue;
    const c = D.compras[a.cod] || [0, 0, 0];
    out.push({ cod: a.cod, nom, u, fam, sub, usado: a.tot, costo: a.costo, comp: c[0], sComp: c[1], docs: c[2], ficha: true });
    vistos.add(a.cod);
  }
  for (const [cod, c] of Object.entries(D.compras)) {
    if (vistos.has(cod)) continue;
    let nom, u, fam, sub;
    if (D.comprados[cod]) [nom, u, fam, sub] = D.comprados[cod];
    else if (D.insumos[cod]) [nom, u, , fam, sub] = D.insumos[cod];
    else continue;
    out.push({ cod, nom, u, fam, sub, usado: 0, costo: 0, comp: c[0], sComp: c[1], docs: c[2], ficha: A.ins.has(cod) });
  }
  for (const r of out) {
    r.dif = r.comp - r.usado; r.peso = Math.max(r.sComp, r.costo);
    const pr = D.insumos[r.cod] ? D.insumos[r.cod][2] : (r.comp ? r.sComp / r.comp : 0);
    r.sDif = Math.abs(r.dif) * pr;
  }
  return out.sort((x, y) => y.peso - x.peso);
}
const alta = r => r.usado > 0 && Math.abs(r.dif) > 0.25 * r.usado && r.sDif >= DIF_MIN_SOLES;
function pintarCompras() {
  const cab = document.getElementById('cc-cabeza'), tb = document.getElementById('cc-filas');
  if (!D.compras_familias.length) {
    document.getElementById('cc-resumen').textContent = 'No se pudieron leer las compras del período (compras.parquet).';
    cab.innerHTML = ''; tb.innerHTML = ''; document.getElementById('cc-pie').textContent = '';
    return;
  }
  const todas = filasCompras();
  const compradas = todas.filter(r => r.comp > 0);
  const sTot = suma(compradas.map(r => r.sComp));
  const usadas = compradas.filter(r => r.usado > 0), sinUso = compradas.filter(r => r.usado <= 0);
  const sUsadas = suma(usadas.map(r => r.sComp));
  document.getElementById('cc-sub').textContent = `Del ${fCorta(P.desde)} al ${fCorta(P.hasta)} · ${famsTexto()} · compras por la fecha del documento`;
  document.getElementById('cc-resumen').innerHTML =
    `<b>${sol(sTot)}</b> comprados en ${compradas.length} productos. Las ventas del período usan ${usadas.length} de ellos: <b>${sol(sUsadas)}</b> (${pct(sUsadas, sTot)}).` +
    (sinUso.length ? ` <b>${sol(suma(sinUso.map(r => r.sComp)))}</b> en ${sinUso.length} producto${sinUso.length === 1 ? '' : 's'} que ninguna venta del período usó.` : ' Todo lo comprado lo usó alguna venta del período.');
  document.getElementById('cc-filtro').innerHTML = FILTROS_C.map(([k, txt]) =>
    `<button class="chipf" type="button" aria-pressed="${k === ccFiltro}" data-f="${k}"${k === 'dif' ? ` title="Más del 25 % de lo que explican las ventas y más de S/ ${DIF_MIN_SOLES}, ordenado por los soles de la diferencia"` : ''}>${txt}</button>`).join('');
  let vis = todas;
  if (ccFiltro === 'sin') vis = vis.filter(r => r.comp > 0 && r.usado <= 0);
  if (ccFiltro === 'dif') vis = vis.filter(alta).sort((x, y) => y.sDif - x.sDif);
  if (ccTxt) vis = vis.filter(r => r.nom.toLowerCase().includes(ccTxt));
  cab.innerHTML = '<tr><th class="rk">#</th><th>Insumo</th><th class="r">Se compró<div class="th-sub">soles</div></th><th class="r">Explican las ventas<div class="th-sub">costo de hoy</div></th><th class="r">Comprado − usado</th></tr>';
  porTandas(tb,vis,(r, i) => {
    const u_ = esc(corta(r.u));
    let dif;
    if (r.usado <= 0) dif = '<span class="dif alta">ninguna venta lo usó</span>';
    else if (r.comp <= 0) dif = `<span class="dif${alta(r) ? ' alta' : ''}">no se compró · −${prom(r.usado)} ${u_}</span>`;
    else dif = `<span class="dif${alta(r) ? ' alta' : ''}">${r.dif >= 0 ? '+' : '−'}${prom(Math.abs(r.dif))} ${u_} · ${r.dif >= 0 ? '+' : '−'}${pct0(Math.abs(r.dif), r.usado)}</span>`;
    if (r.usado > 0 && r.sDif >= 0.5) dif += `<div class="costo-sub">${sol(r.sDif)}</div>`;
    return `<tr${r.ficha ? ` tabindex="0" data-cod="${esc(r.cod)}" title="Abrir su ficha en «Resumen»"` : ' class="sin-ficha"'}>
      <td class="rk num">${i + 1}</td>
      <td><div class="nom">${esc(r.nom)}</div><div class="fam">${esc(cap(r.fam))} · ${esc(r.sub || '')}</div></td>
      <td class="r num">${r.comp ? `${prom(r.comp)}<span class="und">${u_}</span><div class="costo-sub">${sol(r.sComp)}</div>` : '—'}</td>
      <td class="r num">${r.usado ? `${prom(r.usado)}<span class="und">${u_}</span><div class="costo-sub">${sol(r.costo)}</div>` : '—'}</td>
      <td class="r num">${dif}</td></tr>`;
  },'<tr class="sin-ficha"><td colspan="5">Nada con este filtro.</td></tr>');
  recordarFiltros();
  document.getElementById('cc-pie').textContent =
    `${vis.length} de ${todas.length} insumos. Comprar no es usar: el stock del almacén sube y baja entre compras, y hay usos que no pasan por una receta (aceite de freír, comida del personal, pruebas, mermas). Una diferencia chica es normal; una grande en un mes pide mirar (en ámbar: más del 25 % y más de S/ ${DIF_MIN_SOLES}). En la unidad del kardex, la misma de las compras; soles de compra sin IGV, y lo que explican las ventas al costo promedio de hoy.` +
    (UI.vi ? '' : ' Con la venta interna apagada, lo que se compró para ella queda del lado de lo comprado.');
}
document.getElementById('cc-filtro').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; ccFiltro = b.dataset.f; pintarCompras(); });
document.getElementById('cc-buscar').addEventListener('input', e => { ccTxt = e.target.value.trim().toLowerCase(); pintarCompras(); });
const abrirFicha = cod => { UI.vista = 'resumen'; UI.sel = cod; guardar(); pintarVista(); pintarActiva(); };
document.getElementById('cc-filas').addEventListener('click', e => { const tr = e.target.closest('tr[data-cod]'); if (tr) abrirFicha(tr.dataset.cod); });
document.getElementById('cc-filas').addEventListener('keydown', e => { if (e.key === 'Enter') { const tr = e.target.closest('tr[data-cod]'); if (tr) abrirFicha(tr.dataset.cod); } });

// ── cómo se calcula (regla #751): cinco pasos con su cifra y unas reglas ──
// Lo producido contra lo facturado del período, producto por producto
// (regla #605): la cuenta de arriba sale de lo primero.
function notaProduccion() {
  const pr = (D.venta_interna && D.venta_interna.produccion) || [];
  if (!pr.length) return '';
  const filas = pr.map(([pl, u, prod, fact, masa, parte]) =>
    `${esc(pl)}: ${n0(prod)} ${esc(u)} porcionad${prod === 1 ? 'o' : 'os'}, ${n0(fact)} facturad${fact === 1 ? 'o' : 'os'}${masa ? ' (fechado por su masa)' : ''}${parte < 0.995 ? ` (a la venta interna le toca el ${Math.round(parte * 100)} %)` : ''}`);
  return ' En el período: ' + filas.join(' · ') + '.';
}
function pintarMetodo() {
  const R = D.resumen, g = new Map();
  for (const a of A.lista) for (const [k, q] of a.cam) g.set(k, (g.get(k) || 0) + q * D.insumos[a.cod][2]);
  const tot = suma([...g.values()]) || 1, parte = k => Math.round(100 * (g.get(k) || 0) / tot);
  const pasos = [
    ['Plato vendido', `Lo cobrado, por el día del pedido; la hora, la de cada plato${R.hora_de_mesa ? ' (en este parquet, la de la mesa)' : ''}.`, '', 'var(--suave-2)'],
    ['Receta de venta', 'El primer nivel, el del POS (Paloteo de Insumos).', sol(R.costo_nivel1), 'var(--suave-2)'],
    ['Receta base', `Una preparación baja por su receta, hasta ${R.niveles} niveles.`, `${parte('receta')} % <small>del costo llega así</small>`, 'var(--c-receta)'],
    ['Porcionamiento', 'Un corte pasa al insumo entero con el rendimiento real.', `${parte('porc') + parte('mixto')} % <small>del costo</small>`, 'var(--c-porc)'],
    ['Insumo de compra', 'En la unidad del kardex, a precio promedio de hoy.', `${sol(suma(A.lista.map(a => a.costo)))} <small>· ${n0(A.lista.length)} insumos</small>`, 'var(--acento-texto)'],
  ];
  document.getElementById('metodo-flujo').innerHTML = pasos.map(([t, d, v, c]) =>
    `<div class="paso" style="--c:${c}"><span class="t">${t}</span><span class="d">${d}</span>${v ? `<span class="v num">${v}</span>` : ''}</div>`).join('');
  document.getElementById('metodo-puente').innerHTML = `De ${sol(R.costo_nivel1)} al primer nivel a ${sol(R.costo)} en insumos: por las recetas base cierra (el Almacén recuesta cada preparación con sus insumos); la diferencia sale de los porcionamientos, que llevan el rendimiento real y no el costo que el Almacén le puso al corte.`;
  const editadas = PLATOS.filter(p => p[3]);
  const reglas = [
    ['Recetas y precios: los de hoy.', editadas.length
      ? `${editadas.length} plato${editadas.length === 1 ? '' : 's'} cambi${editadas.length === 1 ? 'ó' : 'aron'} de receta desde el ${fCorta(P.desde)} (${esc(editadas.slice(0, 3).map(p => `${p[0]}, ${fCorta(p[3])}`).join(' · '))}${editadas.length > 3 ? '…' : ''}): lo vendido antes se calcula con la nueva. Cada fila lo marca.`
      : 'Editar una receta cambia el consumo de meses pasados, como en el POS.'],
    ['Rendimiento.', `${REND === 'mes' ? 'Ahora, «Último mes»: los porcionamientos del mes; si en el mes no hubo, los de 90 días.' : 'Ahora, «90 días»: los porcionamientos de los 90 días que cierran cada mes.'} Sin ninguno, la receta base; sin receta, los 10 más cercanos. Entre los cortes se reparte por peso, la regla del Almacén.`],
    ['Día y hora.', '«Día de la semana» es un promedio: lo de los lunes entre cuántos lunes hubo.'],
    ['Venta interna.', 'Lo que se produce para Mayta cuenta el día que se produjo, no el que se facturó.' + notaProduccion()],
    ['No es el consumo real.', 'Ése es inventario inicial + compras − inventario final, en Costos; el costo histórico de lo vendido, en Ventas.'],
  ];
  if (R.sin_maestro || R.sin_factor) reglas.push(['Lo que no se pudo bajar.', `${R.sin_maestro} líneas con un insumo que no está en el maestro y ${R.sin_factor} sin factor de conversión: ${sol(R.costo_sin_convertir)} del primer nivel.`]);
  document.getElementById('metodo-txt').innerHTML = reglas.map(([b, t]) => `<p><b>${b}</b> ${t}</p>`).join('');
}

function pintarActiva(){
  document.getElementById('ccn-seleccion').textContent=CONTEXTO;
  if(UI.vista==='tabla'){pintarSegTD();pintarDinamica();}
  else if(UI.vista==='resumen'){pintarFams();pintarModos();pintarCabeza();pintarFilas();pintarDetalle();}
  else pintarCompras();
}
function pintarTodo(){
  const fams=new Set(A.lista.map(a=>D.insumos[a.cod][3]));
  if(tdFam!=='Todas'&&!fams.has(tdFam))tdFam='Todas';
  if(famSel!=='Todas'&&!fams.has(famSel))famSel='Todas';
  pintarResumen();pintarMetodo();pintarActiva();
}
// abre con el primer insumo y su primera preparación desplegados: los tres niveles a la vista
if (!UI.tdInit && A.lista.length) {
  UI.tdInit=true;
  const a0 = A.lista[0];
  const p0 = [...a0.preps.values()].sort((x, y) => y.tot - x.tot)[0];
  tdAbiertos.add('i:' + a0.cod);
  if (p0) tdAbiertos.add('p:' + a0.cod + '|' + p0.prep);
}
// Sólo se dibuja una tanda; el dato y el Excel mantienen todas las filas.
const lotes=new Map();
function porTandas(tb,datos,html,vacio,hasta=0,preservar=false){
  const wrap=tb.closest('.td-wrap,.tabla-wrap'),anterior=lotes.get(tb.id);
  const top=preservar?wrap.scrollTop:0,left=wrap.scrollLeft;
  anterior?.boton.remove();
  const boton=owner.createElement('button');boton.type='button';boton.className='ccn-mas';
  const lote={datos,n:0,boton};lotes.set(tb.id,lote);tb.innerHTML='';
  const sumar=(cantidad=150)=>{
    const fin=Math.min(datos.length,lote.n+cantidad);
    tb.insertAdjacentHTML('beforeend',datos.slice(lote.n,fin).map((x,i)=>html(x,lote.n+i)).join(''));
    lote.n=fin;boton.hidden=fin>=datos.length;
    boton.textContent=`Mostrar más · ${fin} de ${datos.length} filas`;
  };
  if(!datos.length)tb.innerHTML=vacio;
  sumar(Math.max(150,hasta,preservar?anterior?.n||0:0));
  wrap.after(boton);boton.onclick=()=>sumar();
  wrap.onscroll=()=>{if(wrap.scrollTop+wrap.clientHeight>=wrap.scrollHeight-100&&!boton.hidden)sumar();};
  wrap.scrollTop=top;wrap.scrollLeft=left;
}
function recordarFiltros(){
  Object.assign(UI,{tdTxt,tdFam,abiertos:[...tdAbiertos],famSel,txt,ccTxt,ccFiltro});guardar();
}
function resumenVisible(){return A.lista.filter(a=>(famSel==='Todas'||D.insumos[a.cod][3]===famSel)&&(!txt||D.insumos[a.cod][0].toLowerCase().includes(txt)));}
function comprasVisible(){
  let vs=filasCompras();
  if(ccFiltro==='sin')vs=vs.filter(r=>r.comp>0&&r.usado<=0);
  if(ccFiltro==='dif')vs=vs.filter(alta).sort((x,y)=>y.sDif-x.sDif);
  return ccTxt?vs.filter(r=>r.nom.toLowerCase().includes(ccTxt)):vs;
}
function avisoFicha(vis){
  const a=A.ins.get(UI.sel);document.getElementById('ccn-seleccion').textContent=
    a&&!vis.includes(a)?`La ficha de ${D.insumos[a.cod][0]} queda fuera del filtro. Excel conserva su código en «Ficha».`:
    CONTEXTO;
}
function exportar(){
  const hs=[],hoja=(nombre,cabeza,filas)=>hs.push({nombre,cabeza,filas,decimales:6});
  const etiquetas={semana:Array.from({length:NS},(_,i)=>semTitulo(i)+(semParcial(i)?' *':'')),dia:P.finas,mes:P.meses,dsem:DIAS_L,turno:['Almuerzo','Cena'],total:[]}[UI.tdCols];
  const dinamica=[];
  // Los tres niveles se exportan completos, incluso si están plegados en pantalla.
  for(const a of A.lista){
    const [nom,u,pr,fam]=D.insumos[a.cod];if(tdFam!=='Todas'&&fam!==tdFam)continue;
    const bs=[...a.preps.values()].filter(b=>!tdTxt||coincide(nom)||coincide(prepNombre(b.prep))||[...b.platos.values()].some(c=>coincide(PLATOS[c.pid][0])));
    if(!bs.length)continue;
    const factor=UI.tdVal==='soles'?pr:1;
    const row=(tipo,prep,pid,x)=>[tipo,a.cod,nom,u,prep,prepNombre(prep),pid===null?'':PLATOS[pid][0],UI.tdVal==='soles'?'S/':u,x.tot*factor,...cubetas(x).map(q=>q*factor)];
    dinamica.push(row('Insumo','',null,a));
    for(const b of bs){dinamica.push(row('Preparación',b.prep,null,b));for(const c of b.platos.values())if(!tdTxt||coincide(nom)||coincide(prepNombre(b.prep))||coincide(PLATOS[c.pid][0]))dinamica.push(row('Plato',b.prep,c.pid,c));}
  }
  hoja('Dinámica',['Nivel','Código insumo','Insumo','Unidad kardex','Código preparación','Preparación','Plato','Unidad del valor','Total',...etiquetas],dinamica);
  const resumen=resumenVisible();
  const series=a=>UI.modo==='dias'?diasDe(a):UI.modo==='horas'?horasDe(a):semanasDe(a);
  const eje=UI.modo==='dias'?DIAS_L:UI.modo==='horas'?D.horas.map(h=>h+' h'):Array.from({length:LARGO?NM:NS},(_,i)=>tituloSerie(i));
  hoja('Insumos',['Código','Insumo','Unidad','Familia','Subfamilia','Cantidad','Costo actual S/','Venta interna cantidad',...eje],resumen.map(a=>[a.cod,...D.insumos[a.cod].slice(0,2),...D.insumos[a.cod].slice(3,5),a.tot,a.costo,a.vi,...series(a)]));
  hoja('Compras',['Código','Insumo','Unidad','Familia','Subfamilia','Comprado','Compra sin IGV S/','Documentos','Consumo estimado','Costo actual S/','Comprado menos usado','Diferencia absoluta al precio actual S/'],comprasVisible().map(r=>[r.cod,r.nom,r.u,r.fam,r.sub,r.comp,r.sComp,r.docs,r.usado,r.costo,r.dif,r.sDif]));
  const a=A.ins.get(UI.sel),ficha=[];
  if(a)for(const b of a.preps.values())for(const c of b.platos.values())ficha.push([a.cod,D.insumos[a.cod][0],D.insumos[a.cod][1],b.prep,prepNombre(b.prep),PLATOS[c.pid][0],!!PLATOS[c.pid][1]?'Sí':'No',c.tot,c.tot*D.insumos[a.cod][2],PLATOS[c.pid][3]||'']);
  hoja('Ficha',['Código','Insumo','Unidad','Código preparación','Preparación','Plato','Venta interna','Consumo estimado','Costo actual S/','Receta editada desde'],ficha);
  const flujos=D.filas.filter(f=>UI.vi||!PLATOS[f[2]][1]);
  hoja('Flujos',['Código','Insumo','Unidad','Preparación','Plato','Primer nivel','Camino','Tipo unidad','Cantidad','Costo actual S/',...P.finas],flujos.map(f=>{const vv=Array(NF).fill(0);f[6].forEach(([i,q])=>vv[i]+=q);const q=suma(f[9]);return[f[0],D.insumos[f[0]][0],D.insumos[f[0]][1],prepNombre(f[1]),PLATOS[f[2]][0],prepNombre(f[3]),CAMINOS[f[4]],f[5],q,q*D.insumos[f[0]][2],...vv];}));
  const porcs=[];
  for(const [cod,preps]of Object.entries(D.porcs||{}))for(const [prep,z]of Object.entries(preps))for(const po of z[5]||[])porcs.push([cod,D.insumos[cod]?.[0]||'',D.insumos[cod]?.[1]||'',prep,prepNombre(prep),z[0],z[1],z[2],z[3],z[4]?"Sí":"No",...po]);
  hoja('Porcionamientos',['Código insumo','Insumo','Unidad entrada','Código corte','Corte','N documentos insumo y corte','N documentos del corte','Desde','Hasta','Sólo respaldo','Documento','Fecha','Cantidad porcionada','Asignado al corte','Cantidad corte'],porcs);
  // La cuenta de cada corte, mes por mes (regla #751).
  const cuentas=[];
  for(const a of A.lista)for(const b of a.preps.values()){const cu=cuentaCorte(a.cod,b);if(!cu)continue;
    for(const x of cu.meses){const real=x.pesoE>0&&x.entra>0?1-x.pesoE/x.entra:'';const esp=MERMAS[a.cod];
      cuentas.push([a.cod,D.insumos[a.cod][0],D.insumos[a.cod][1],b.prep,prepNombre(b.prep),x.m,x.und,x.r,x.q,x.entra,x.tot,x.saleE,x.pesoE,real,x.n,x.desde,x.hasta,x.alcance,esp??'',esp!=null&&real!==''?x.q*(1-real)/(1-esp/100):'']);}}
  hoja('Rendimientos',['Código insumo','Insumo','Unidad entrada','Código corte','Corte','Mes','Unidades usadas','Rendimiento','Usado del insumo','Puso el insumo','Unidades del corte','Unidades de este insumo','Peso de esas unidades','Merma real','Porcionamientos','Desde','Hasta','Ventana','Merma esperada %','Usado con la merma esperada'],cuentas);
  hoja('Horas',['Código','Insumo','Unidad','Hora','Promedio por día'],A.lista.flatMap(a=>horasDe(a).map((q,i)=>[a.cod,D.insumos[a.cod][0],D.insumos[a.cod][1],D.horas[i],q])));
  hoja('Contexto',['Concepto','Valor'],[
    ['Desde incluido',P.desde],['Hasta incluido',P.hasta],['Vista',UI.vista],['Venta interna',UI.vi?'Incluida':'Excluida'],
    ['Rendimiento',REND==='mes'?'Último mes: porcionamientos del mes; si no hubo, los de 90 días':'90 días: porcionamientos de los 90 días que cierran cada mes'],
    ['Mermas esperadas',JSON.stringify(MERMAS)],
    ['Tabla: columnas',UI.tdCols],['Tabla: valor',UI.tdVal],['Tabla: familia',tdFam],['Tabla: búsqueda',tdTxt],
    ['Resumen: modo',UI.modo],['Resumen: familia',famSel],['Resumen: búsqueda',txt],['Ficha: código',UI.sel||''],
    ['Compras: filtro',ccFiltro],['Compras: búsqueda',ccTxt],
    ['Filtros de la página',JSON.stringify(component.data.contexto||{})],
    ['Base','Consumo estimado con recetas y precios promedio actuales. Compras por fecha del documento, sin IGV.'],
    ['Precisión','Datos de la vista cuantizados a 6 decimales por el adaptador original; Excel conserva 6 decimales.'],
    ['Unidades','Cantidad por insumo y unidad kardex; no se suman cantidades entre unidades.'],
    ['Jerarquía','Total de un insumo incluye sus hijos. No sumar niveles. Búsqueda de hijo conserva el total de su padre.'],
    ['Promedios','Día de semana entre sus ocurrencias en el rango; horas entre días del rango.'],
    ['Rastro','Porcionamientos incluye hasta 60 documentos por par insumo/corte, como la fuente de la vista; el cálculo usa la referencia completa.'],
    ['Flujos y horas','Fuentes completas de las familias de la página y venta interna elegida, sin filtros locales.'],
    ['Ediciones de recetas','Desde el inicio del rango hasta hoy; pueden ser posteriores al fin histórico.'],
  ]);return hs;
}
document.getElementById('ccn-excel').onclick=()=>bajar(`consumo_${P.desde}_${P.hasta}.xlsx`,libro(exportar()));

pintarVista();
pintarTodo();
// «Rendimiento» rehace el cálculo en Python; la merma esperada se guarda en R2.
{
  const seg = document.getElementById('rend-seg');
  seg.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.r === REND));
  seg.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b || b.dataset.r === REND || seg.classList.contains('pidiendo')) return;
    seg.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); seg.classList.add('pidiendo');
    component.setTriggerValue('rendimiento', b.dataset.r);
  });
}
raiz.addEventListener('click', e => {
  const b = e.target.closest('[data-porcs]'); if (!b) return;
  e.stopPropagation(); const k = b.dataset.porcs; porcsVer.has(k) ? porcsVer.delete(k) : porcsVer.add(k);
  pintarDinamica(); const n = raiz.querySelector(`[data-porcs="${CSS.escape(k)}"]`); if (n) n.focus({ preventScroll: true });
}, { signal: abort.signal, capture: true });
raiz.addEventListener('change', e => {
  const i = e.target.closest('input[data-merma]'); if (!i || i.disabled) return;
  const t = i.value.trim(), v = t === '' ? null : Number(t.replace(',', '.'));
  if (v !== null && !(v >= 0 && v < 90)) { i.setCustomValidity('Entre 0 y 89.9 %'); i.reportValidity(); return; }
  i.setCustomValidity(''); i.disabled = true; i.closest('label')?.classList.add('guardando');
  component.setTriggerValue('merma', { cod: i.dataset.merma, pct: v });
}, { signal: abort.signal });

  const cleanup=()=>{abort.abort();observers.forEach(r=>r.disconnect());};
  window.__consumoNative={raiz,datos:D,UI,arbolDe,cubetas,filasCompras,cleanup,pintarTodo,exportar,horasDe,mapaDe,diasDe,semanasDe,resumenVisible,comprasVisible,lotes,tdAbiertos,cuentaCorte,mermaDe,porcsVer,A:()=>A};
  return cleanup;
}
