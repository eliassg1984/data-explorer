// Ventas › «Análisis por hora» (regla #704).
//
// La monta graficos/ventas_horario.py::_ventas_horario con st.components.v2
// (sin iframe, estilos en un shadow root), DOS VECES: la tarjeta del mapa
// (`parte: "horas"`, con los datos) y la de la comparación de franjas
// (`parte: "franjas"`, sólo el `sello`). Es la forma del boceto 4 aprobado
// (https://claude.ai/artifact/McRvFx5rdn1tKz8xfzrWeq).
//
// UN CEREBRO, DOS MONTAJES. Sin iframe las dos piezas comparten `window`:
// el montaje del mapa deja en `window.__vhHora` el estado (`S`), las raíces
// de las dos tarjetas y las funciones que dibujan, y el de las franjas sólo
// le entrega su raíz. Así los pedidos viajan una vez, y una franja que se
// arrastra en el mapa aparece abajo sin una corrida. Si el de las franjas
// llega primero, deja su raíz en espera (`pend2`) y el mapa la adopta.
//
// Python manda en `data`: `rango`, `ultimo`, `ventanas` (lo cargado: el
// rango con 13 semanas antes y el mismo rango 364 días antes), `dias`,
// `canales`, `tdesc`, `prods` ([nombre, grupo, subgrupo, área]), `P` (un
// pedido: CAMPOS_P de ventas_horario.py, en ESE orden), `L` (una línea:
// CAMPOS_L), `feriados`, `grupos_raros` y, a veces, `ir` (el salto desde
// «Análisis de platos»). Todo lo demás se resuelve acá sin una corrida.
//
// LAS CUENTAS DE LA REFERENCIA: lo normal es la mediana de la misma hora y
// día de la semana en las 8 semanas anteriores (#536); el año pasado, 364
// días antes (#659); «contra» suma la venta día × hora y la compara con la
// suma de las referencias de cada día × hora (una cuenta para el indicador y
// los paneles lado a lado). Una celda chica (menos de 0,3 × el p75 de las
// celdas) va en gris: un 100 % sobre S/ 20 no dice nada.

const P_DIA = 0, P_ABRE = 1, P_CANAL = 2, P_PAX = 3, P_DUR = 4, P_DIA_COBRO = 5, P_COBRO = 6, P_LOCAL = 7;
const L_PED = 0, L_PROD = 1, L_CANT = 2, L_VENTA = 3, L_DESC = 4, L_TDESC = 5;
// `_v2`: desde que las franjas de entrada son las cenas que más venden (las
// de ejemplo de antes quedaron guardadas con la clave vieja).
const CLAVE = 'vh_hora_est_v2';
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const DIAS_L = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const DIAS_PL = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábados', 'domingos'];
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const MES_L = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const FCOL = ['var(--f0)', 'var(--f1)', 'var(--f2)', 'var(--f3)'];
const SCOL = (i) => `var(--s${Math.min(i, 7)})`;
const MIN_UNID = 10;
const SEMANAS = [1, 2, 3, 4, 5, 6, 7, 8];
const DIAS_AP = 364;
const MADRUGADA = 6;
const MED = {
  venta: ['Venta', (v) => soles(v), true], cant: ['Unidades', (v) => fn(v), true], mesas: ['Mesas', (v) => v.toFixed(v < 10 ? 1 : 0), false],
  pax: ['Personas', (v) => v.toFixed(v < 10 ? 1 : 0), false], gasto: ['Gasto/persona', (v) => `S/ ${v.toFixed(0)}`, false], desc: ['Descuento', (v) => soles(v), true],
};
const REF_NOM = { normal: 'lo normal', ap: 'el año pasado', otro: 'otro período' };
const N_CENAS = 3;
const PISO_CENA = 0.25;

const G = (window.__vhHora = window.__vhHora || {});

// ── Ayudas ───────────────────────────────────────────────────────────────
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const k = (v) => { const a = Math.abs(v); return a >= 1000 ? `${(v / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : (a < 10 && a % 1 ? v.toFixed(1) : Math.round(v).toString()); };
const soles = (v) => `S/ ${Math.round(v).toLocaleString('en-US')}`;
const fn = (v) => Math.round(v).toLocaleString('en-US');
const pc = (v, d = 0) => (isFinite(v) ? `${(v * 100).toFixed(d)}%` : '—');
const hh = (h) => (h === 12 ? '12 pm' : h === 24 || h === 0 ? '12 am' : h > 12 ? `${h - 12} pm` : `${h} am`);
const hm = (min) => { const h = Math.floor(min / 60) % 24, h12 = h % 12 === 0 ? 12 : h % 12; return `${h12}:${String(min % 60).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`; };
const sl = (s) => (s >= 48 ? '12:00 am' : hm(s * 30));
const dow = (s) => (new Date(s + 'T12:00:00').getDay() + 6) % 7;
const mas = (s, n) => { const d = new Date(s + 'T12:00:00'); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const mediana = (xs) => { const o = xs.filter((x) => isFinite(x)).sort((a, b) => a - b); if (!o.length) return NaN; const m = o.length >> 1; return o.length % 2 ? o[m] : (o[m - 1] + o[m]) / 2; };
const esNoche = (h) => h >= 17 || h < MADRUGADA;
function leer() { try { const v = localStorage.getItem(CLAVE); return v ? JSON.parse(v) : {}; } catch (_) { return {}; } }
function guardar() {
  const S = G.S; if (!S) return;
  // Mientras las franjas sean las de entrada no se guardan: se vuelven a
  // calcular con cada rango.
  try { localStorage.setItem(CLAVE, JSON.stringify({ franjas: S.franjasAuto ? null : S.franjas, nextId: S.nextId, salon: S.salon, forma: S.forma, cifras: S.cifras, paneles: [...S.paneles] })); } catch (_) { /* sin almacenamiento */ }
}

// ── El estado: abre siempre en lo de siempre; se recuerdan las franjas y la forma ──
function estadoInicial() {
  const r = leer();
  return {
    preg: 'cuando', modo: 'semana', celda: 'prom', por: 'platos', colsVer: 'hora', medida: 'venta', comp: 'nada', mostrar: 'mapa', otro: 3,
    paneles: new Set(Array.isArray(r.paneles) ? r.paneles : ['normal', 'ap']), canal: 'todos', ambito: '', base: 'pedido',
    // Abre con eventos y sin venta interna (decisión del usuario, 2026-10-22).
    eventos: true, vinterna: false,
    cifras: !!r.cifras, forma: r.forma === 'puntos' ? 'puntos' : 'mosaico',
    pop: false, menu: false, tab: 'resumen', sel: null, item: null, salon: r.salon > 0 ? r.salon : null, ampliar: false, chicos: false, todos: false,
    areasUnid: false, areasAuto: false, ctab: 'cifras', fsel: null, abiertos: new Set(), arbol: 'venta', editando: null, borrador: null,
    // Sin franjas propias, las de entrada: las cenas que más venden (`cenasMayores`).
    franjas: Array.isArray(r.franjas) ? r.franjas.slice(0, 4) : [], franjasAuto: !Array.isArray(r.franjas),
    nextId: r.nextId > 0 ? r.nextId : 1,
    // El mapa abre sin los bordes de las franjas: el interruptor «Franjas» los
    // muestra, y sólo con él prendido arrastrar crea o redibuja una.
    verFranjas: false, factiva: null,
  };
}

// ── Los datos ────────────────────────────────────────────────────────────
let D = null, S = null, PRODS = [], GRUPOS = [], SUBS = [], RAW = [], FER = new Set(), RAROS = new Set();
let INI, FIN, DIAS_R = [], ANIO = 0, HORAS = [];
let PORDIA = new Map(), IDX = new Map(), RAWDIA = new Map();
const $ = (id) => (G.R1 && G.R1.querySelector('#' + id)) || (G.R2 && G.R2.querySelector('#' + id));
const fecha = (s) => { const [y, m, d] = s.split('-').map(Number); return `${d} ${MES[m - 1]}${y !== ANIO ? ' ' + y : ''}`; };
const rangoTxt = () => `${fecha(INI)} – ${fecha(FIN)}${Number(FIN.slice(0, 4)) === ANIO ? ' ' + ANIO : ''}`;
const cubre = (d) => D.ventanas.some(([a, b]) => d >= a && d <= b);
function aviso(t, raiz) {
  const e = (raiz || G.R1 || G.R2)?.querySelector('[data-zona="toast"]'); if (!e) return;
  e.textContent = t; e.style.display = 'block'; clearTimeout(aviso.t); aviso.t = setTimeout(() => { e.style.display = 'none'; }, 3800);
}
function cargar(data) {
  D = data;
  [INI, FIN] = D.rango; ANIO = Number(FIN.slice(0, 4));
  DIAS_R = []; for (let d = INI; d <= FIN; d = mas(d, 1)) DIAS_R.push(d);
  FER = new Set(D.feriados);
  RAROS = new Set(D.grupos_raros || ['Venta Interna', 'Eventos']);
  PRODS = D.prods.map((p) => ({ nombre: p[0], grupo: p[1], sub: p[2], area: p[3] }));
  GRUPOS = [...new Set(PRODS.map((p) => p.grupo))].sort();
  SUBS = [...new Set(PRODS.map((p) => p.sub))].sort();
  RAW = D.P.map((p, i) => ({ i, abreDia: D.dias[p[P_DIA]], abre: p[P_ABRE], canal: p[P_CANAL], pax: p[P_PAX] || 0, dur: p[P_DUR], cobDia: D.dias[p[P_DIA_COBRO]], cob: p[P_COBRO], local: !!p[P_LOCAL], lin: [] }));
  for (const l of D.L) RAW[l[L_PED]].lin.push(l);
}

// ── Filtros y sumas ──────────────────────────────────────────────────────
// Eventos y Venta Interna son dos interruptores: abre con eventos y sin venta interna.
const esEvento = (g) => g === 'Eventos', esVI = (g) => g === 'Venta Interna';
function lineaOk(l, amb) {
  const p = PRODS[l[L_PROD]];
  if (!S.eventos && esEvento(p.grupo)) return false;
  if (!S.vinterna && esVI(p.grupo)) return false;
  if (amb) { const t = amb.slice(0, 1), v = amb.slice(2); if (t === 'g' && p.grupo !== v) return false; if (t === 's' && p.sub !== v) return false; }
  return true;
}
const canalOk = (c, can) => can === 'todos' || D.canales[c] === can;
const lugar = (o) => (S.base === 'cobro' ? [o.cobDia, o.cob] : [o.abreDia, o.abre]);
function vacio() { return { venta: 0, cant: 0, desc: 0, mesas: 0, pax: 0, ventaCli: 0, raro: 0, n: 0 }; }
function filtrar(o, can, amb) {
  if (!canalOk(o.canal, can)) return null;
  const [dia0, min] = lugar(o);
  // Lo pedido antes de las 6 es de la noche anterior (consumo_recetas.HORA_MADRUGADA).
  const dia = min < MADRUGADA * 60 ? mas(dia0, -1) : dia0;
  const f = { o, dia, min, venta: 0, cant: 0, desc: 0, pax: o.pax, mesa: o.local && o.pax > 0, lin: [] };
  for (const l of o.lin) if (lineaOk(l, amb)) { f.venta += l[L_VENTA]; f.cant += l[L_CANT]; f.desc += l[L_DESC]; f.lin.push(l); }
  return f.lin.length ? f : null;
}
function sumar(a, f) {
  a.venta += f.venta; a.cant += f.cant; a.desc += f.desc; a.n++;
  if (f.pax > 0) { a.pax += f.pax; a.ventaCli += f.venta; }
  if (f.mesa) a.mesas++;
  for (const l of f.lin) { if (RAROS.has(PRODS[l[L_PROD]].grupo)) a.raro += l[L_VENTA]; }
}
function construir() {
  PORDIA = new Map(); IDX = new Map(); RAWDIA = new Map();
  const horas = new Set();
  const enRango = new Set(DIAS_R);
  for (const o of RAW) {
    const [dia] = lugar(o);
    if (!RAWDIA.has(dia)) RAWDIA.set(dia, []); RAWDIA.get(dia).push(o);
    const f = filtrar(o, S.canal, S.ambito); if (!f) continue;
    if (!PORDIA.has(f.dia)) PORDIA.set(f.dia, []); PORDIA.get(f.dia).push(f);
    const h = Math.floor(f.min / 60);
    if (enRango.has(f.dia)) horas.add(h);
    const key = f.dia + '|' + h; let a = IDX.get(key); if (!a) { a = vacio(); IDX.set(key, a); } sumar(a, f);
  }
  // Las horas con venta en el rango, en el orden del día de servicio (las de
  // la madrugada al final) y SIN huecos: una hora sin venta entre dos que
  // tienen se ve, y dice «sin ventas a esta hora».
  const orden = (h) => (h - MADRUGADA + 24) % 24;
  const ks = [...horas].map(orden);
  if (!ks.length) { HORAS = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]; return; }
  HORAS = []; for (let x = Math.min(...ks); x <= Math.max(...ks); x++) HORAS.push((x + MADRUGADA) % 24);
}
function valor(a, med = S.medida) { if (!a) return NaN; if (med === 'gasto') return a.pax ? (a.ventaCli > 0 ? a.ventaCli : a.venta) / a.pax : NaN; return a[med]; }
function agg(dias, h) { const a = vacio(); for (const d of dias) { const x = IDX.get(d + '|' + h); if (x) for (const q in a) a[q] += x[q]; } return a; }
const div = (a, n) => { const o = {}; for (const q in a) o[q] = a[q] / n; return o; };
const correr = (dias, n) => dias.map((d) => mas(d, n));
const corrimiento = (ref) => (ref === 'ap' ? -DIAS_AP : -7 * S.otro);
function disponible(ref, dias = DIAS_R) {
  if (ref === 'normal') return correr(dias, -56).every(cubre) && dias.every(cubre);
  return correr(dias, corrimiento(ref)).every(cubre);
}
function refCelda(ref, dias, h, divisor) {
  if (ref === 'normal') return mediana(SEMANAS.map((s) => valor(div(agg(correr(dias, -7 * s), h), divisor))));
  return valor(div(agg(correr(dias, corrimiento(ref)), h), divisor));
}
// «Contra»: UNA cuenta para el indicador y los paneles lado a lado.
function contra(ref) {
  let a = 0, r = 0;
  for (const d of DIAS_R) for (const h of HORAS) {
    a += agg([d], h).venta;
    r += ref === 'normal' ? mediana(SEMANAS.map((s) => agg([mas(d, -7 * s)], h).venta)) : agg([mas(d, corrimiento(ref))], h).venta;
  }
  return r ? a / r - 1 : NaN;
}

// ── Columnas del mapa ────────────────────────────────────────────────────
function columnas(modo = S.modo) {
  if (modo === 'dia') return DIAS_R.map((d) => ({ id: d, dias: [d], rot: `${DIAS[dow(d)][0]} ${Number(d.slice(8))}`, fer: FER.has(d) }));
  if (modo === 'mes') {
    const m = new Map(); for (const d of DIAS_R) { const kk = d.slice(0, 7); if (!m.has(kk)) m.set(kk, []); m.get(kk).push(d); }
    return [...m.entries()].map(([kk, ds]) => { const [y, mm] = kk.split('-').map(Number); const dim = new Date(y, mm, 0).getDate(); return { id: kk, dias: ds, rot: `${MES[mm - 1]}${ds.length < dim ? '*' : ''}` }; });
  }
  return DIAS.map((r, w) => ({ id: w, dias: DIAS_R.filter((d) => dow(d) === w), rot: r }));
}
const divisorDe = (c) => (S.modo === 'dia' || S.celda === 'total' ? 1 : Math.max(1, c.dias.length));
function celdas(cols) { return cols.map((c) => ({ ...c, h: HORAS.map((h) => { const a = div(agg(c.dias, h), divisorDe(c)); return { h, a, v: valor(a) }; }) })); }

// ── Franjas ──────────────────────────────────────────────────────────────
const cruza = (f) => f.hasta <= f.desde;
const enFranja = (f, s) => (cruza(f) ? s >= f.desde || s < f.hasta : s >= f.desde && s < f.hasta);
const diasDe = (f, dias = DIAS_R) => (f.tipo === 'semana' ? dias.filter((d) => f.dias.includes(dow(d))) : f.fechas.filter((d) => d >= dias[0] && d <= dias[dias.length - 1]).sort());
const filtrosDe = (f) => ({ can: f.canal ?? S.canal, amb: f.ambito ?? S.ambito });
function describir(f) {
  const ds = f.tipo === 'semana' ? (f.dias.length === 7 ? 'Todos los días' : f.dias.slice().sort().map((w) => DIAS[w]).join(', '))
    : f.fechas.length === 1 ? fecha(f.fechas[0]) : `${f.fechas.length} días sueltos`;
  return `${ds} · ${sl(f.desde)} – ${sl(f.hasta)}`;
}
function nombreAuto(f) {
  const w = f.dias.slice().sort(), seguidos = w.length >= 3 && w[w.length - 1] - w[0] === w.length - 1;
  const ds = f.tipo === 'semana' ? (w.length === 7 ? 'Todos los días' : seguidos ? `${DIAS[w[0]]} a ${DIAS[w[w.length - 1]]}` : w.map((x) => DIAS[x]).join(', '))
    : f.fechas.length === 1 ? fecha(f.fechas[0]) : `${f.fechas.length} días`;
  const corto = (x) => sl(x).replace(':00', ''), a = corto(f.desde), b = corto(f.hasta);
  return `${ds} · ${a.slice(-2) === b.slice(-2) ? a.slice(0, -3) : a} – ${b}`;
}
function propios(f) { const p = []; if (f.canal !== null) p.push(f.canal === 'todos' ? 'todos los canales' : f.canal); if (f.ambito !== null) p.push(f.ambito ? f.ambito.slice(2) : 'toda la carta'); return p.join(' · '); }
function sumaFranja(f, dias) {
  // Una franja que cruza la medianoche cuenta en el día en que EMPEZÓ, y
  // mira los pedidos por su día de calendario (no el de servicio).
  const { can, amb } = filtrosDe(f), set = new Set(dias), a = vacio(), lin = [], porDia = new Map(dias.map((d) => [d, { venta: 0, n: 0 }]));
  const mirar = new Set(dias); if (cruza(f)) for (const d of dias) mirar.add(mas(d, 1));
  for (const d of mirar) for (const o of RAWDIA.get(d) || []) {
    const [dia, min] = lugar(o), s = Math.floor(min / 30);
    if (!enFranja(f, s)) continue;
    const delDia = cruza(f) && s < f.hasta ? mas(dia, -1) : dia;
    if (!set.has(delDia)) continue;
    const x = filtrar(o, can, amb); if (!x) continue;
    sumar(a, x); lin.push(...x.lin); const pd = porDia.get(delDia); pd.venta += x.venta; pd.n++;
  }
  return { a, lin, porDia };
}
function cifrasFranja(f) {
  const dias = diasDe(f), n = Math.max(1, dias.length), act = sumaFranja(f, dias);
  const normal = disponible('normal', dias) ? mediana(SEMANAS.map((s) => sumaFranja(f, correr(dias, -7 * s)).a.venta / n)) : NaN;
  const ap = disponible('ap', dias) ? sumaFranja(f, correr(dias, -DIAS_AP)).a.venta / n : NaN;
  return { dias, n: dias.length, ...act, porDiaV: act.a.venta / n, normal, ap };
}
function cenasMayores() {
  // Las franjas de entrada: las N_CENAS noches de la semana que más venden en
  // el rango (venta por día, con los filtros de la vista), cada una en el
  // horario de la cena — las horas de la noche, seguidas, con al menos un
  // cuarto (PISO_CENA) de la venta de la hora pico.
  const porHora = new Map();
  for (const d of DIAS_R) for (const f of PORDIA.get(d) || []) { const h = Math.floor(f.min / 60); if (esNoche(h)) porHora.set(h, (porHora.get(h) || 0) + f.venta); }
  if (!porHora.size) return [];
  const orden = (h) => (h - MADRUGADA + 24) % 24;
  const horas = [...porHora.keys()].sort((a, b) => orden(a) - orden(b));
  const pico = horas.reduce((p, h) => (porHora.get(h) > porHora.get(p) ? h : p), horas[0]);
  const piso = PISO_CENA * porHora.get(pico);
  let i0 = horas.indexOf(pico), i1 = i0;
  while (i0 > 0 && orden(horas[i0 - 1]) === orden(horas[i0]) - 1 && porHora.get(horas[i0 - 1]) >= piso) i0--;
  while (i1 < horas.length - 1 && orden(horas[i1 + 1]) === orden(horas[i1]) + 1 && porHora.get(horas[i1 + 1]) >= piso) i1++;
  const base = { tipo: 'semana', fechas: [], desde: horas[i0] * 2, hasta: ((horas[i1] + 1) * 2) % 48 || 48, canal: null, ambito: null };
  const porDia = DIAS.map((_, w) => { const ds = DIAS_R.filter((d) => dow(d) === w); return ds.length ? sumaFranja({ ...base, dias: [w] }, ds).a.venta / ds.length : 0; });
  return porDia.map((v, w) => [v, w]).filter(([v]) => v > 0).sort((a, b) => b[0] - a[0]).slice(0, N_CENAS)
    .map(([, w], i) => ({ ...base, id: i + 1, dias: [w], nombre: `Cena del ${DIAS_L[w]}`, nombreAuto: true }));
}
function nuevaFranja(base, raiz) {
  if (S.franjas.length >= 4) { aviso('Hasta 4 franjas a la vez: quitá una en la tarjeta de abajo para crear otra.', raiz); return null; }
  const f = Object.assign({ nombre: '', tipo: 'semana', dias: [], fechas: [], desde: 38, hasta: 46, canal: null, ambito: null }, base, { id: S.nextId++ });
  if (!f.nombre) { f.nombre = nombreAuto(f); f.nombreAuto = true; }
  S.franjas.push(f); S.fsel = f.id; S.franjasAuto = false; guardar(); return f;
}

// ── Lo general: cabecera, Más filtros, Medir, Comparar ──────────────────
function filtrosTxt() { const p = []; if (S.canal !== 'todos') p.push(S.canal); if (S.ambito) p.push(S.ambito.slice(2)); if (S.base === 'cobro') p.push('hora del cobro'); if (!S.eventos) p.push('sin eventos'); if (S.vinterna) p.push('con venta interna'); return p.join(' · '); }
function seg(acc, ops, act, off = {}, cls = 'seg') { return `<div class="${cls}">${ops.map(([v, r]) => `<button type="button" data-acc="${acc}" data-v="${esc(v)}" class="${String(v) === String(act) ? 'on' : ''}" ${off[v] ? `disabled title="${esc(off[v])}"` : ''}>${esc(r)}</button>`).join('')}</div>`; }
function opcionesAmbito(sel, heredar) {
  return `${heredar ? `<option value="__"${sel === null ? ' selected' : ''}>Como el resto de la vista</option>` : ''}<option value=""${sel === '' ? ' selected' : ''}>Toda la carta</option><optgroup label="Grupo">${GRUPOS.map((g) => `<option value="g:${esc(g)}"${sel === 'g:' + g ? ' selected' : ''}>${esc(g)}</option>`).join('')}</optgroup><optgroup label="Subgrupo">${SUBS.map((s) => `<option value="s:${esc(s)}"${sel === 's:' + s ? ' selected' : ''}>${esc(s)}</option>`).join('')}</optgroup>`;
}
const delPedido = (m) => !MED[m][2];
function general() {
  $('preg').innerHTML = seg('preg', [['cuando', 'Cuándo se vende'], ['que', 'Qué se vende a cada hora']], S.preg, {}, 'modos');
  const nAct = [S.canal !== 'todos', !!S.ambito, S.base === 'cobro', !S.eventos, S.vinterna].filter(Boolean).length;
  $('activos').textContent = filtrosTxt();
  $('mas').className = `mas${S.pop ? ' on' : ''}`; $('mas').innerHTML = `Más filtros ${nAct ? `<b>${nAct}</b>` : ''} ▾`;
  $('popw').innerHTML = S.pop ? `<div class="pop" id="pop">
    <div class="fila"><span>Canal</span>${seg('canal', [['todos', 'Todos']].concat(D.canales.map((c) => [c, c || 'Sin canal'])), S.canal)}</div>
    <div class="fila"><span>Ámbito</span><select class="sel" id="ambito" style="max-width:100%">${opcionesAmbito(S.ambito, false)}</select></div>
    <div class="fila"><span>Hora de la venta</span>${seg('base', [['pedido', 'Cuando se abrió el pedido'], ['cobro', 'Cuando se cobró']], S.base)}</div>
    <div class="fila"><span>Qué entra</span><label class="sw"><input type="checkbox" id="eventos" ${S.eventos ? 'checked' : ''}> Eventos (un punto naranja los marca en el mapa)</label><label class="sw"><input type="checkbox" id="vinterna" ${S.vinterna ? 'checked' : ''}> Venta interna</label></div>
    <div class="acc"><button type="button" class="btn sec peq" id="limpiar">Volver a lo de siempre</button><button type="button" class="btn peq" id="cerrar-pop">Listo</button></div></div>` : '';
  const porPedido = S.preg === 'que' ? 'Es del pedido, no del plato: una mesa de cuatro no le reparte una persona a cada plato.' : '';
  const off = (r) => (disponible(r) ? '' : 'No hay datos cargados para ese período');
  const offOtro = (n) => (correr(DIAS_R, -7 * n).every(cubre) ? '' : 'No hay datos cargados para ese período');
  const opsOtro = [3, 8, 13].map((n) => `<option value="${n}"${S.otro === n ? ' selected' : ''}${offOtro(n) ? ' disabled' : ''}>${n} semanas antes (${fecha(mas(INI, -7 * n))} – ${fecha(mas(FIN, -7 * n))})</option>`).join('');
  $('ctrl').innerHTML = `<div class="g"><span class="rot">Medir</span>${seg('medida', Object.entries(MED).map(([kk, v]) => [kk, v[0]]), S.medida, { mesas: porPedido, pax: porPedido, gasto: porPedido })}</div>
    <div class="g"><span class="rot">Comparar con</span>${seg('comp', [['nada', 'Nada'], ['normal', 'Lo normal'], ['ap', 'Año pasado'], ['otro', 'Otro período']], S.comp, { normal: off('normal'), ap: off('ap') })}${S.comp === 'otro' ? `<select class="sel" id="otro">${opsOtro}</select>` : ''}</div>`;
}

// ── Indicadores ──────────────────────────────────────────────────────────
function kpis() {
  const porHora = HORAS.map(() => 0), porDow = DIAS.map(() => 0);
  let total = 0, pax = 0, mesas = 0, cli = 0;
  for (const d of DIAS_R) for (const f of PORDIA.get(d) || []) { const i = HORAS.indexOf(Math.floor(f.min / 60)); if (i >= 0) porHora[i] += f.venta; porDow[dow(d)] += f.venta; total += f.venta; if (f.pax > 0) { pax += f.pax; cli += f.venta; } if (f.mesa) mesas++; }
  const nDow = DIAS.map((_, w) => DIAS_R.filter((d) => dow(d) === w).length), prom = porDow.map((v, w) => (nDow[w] ? v / nDow[w] : NaN));
  const conDias = prom.map((v, w) => [v, w]).filter(([v]) => isFinite(v));
  const ih = porHora.indexOf(Math.max(...porHora));
  const wMax = conDias.reduce((p, q) => (q[0] > p[0] ? q : p), [-Infinity, 0])[1], wMin = conDias.reduce((p, q) => (q[0] < p[0] ? q : p), [Infinity, 0])[1];
  const mediodia = porHora.filter((_, i) => !esNoche(HORAS[i])).reduce((a, b) => a + b, 0);
  const ref = S.comp === 'nada' ? 'normal' : S.comp, vs = disponible(ref) ? contra(ref) : NaN;
  const tot = total || 1;
  $('kpis').innerHTML = `
    <div class="kpi"><span class="r">Venta · ${esc(rangoTxt())}</span><span class="v">${soles(total)}</span><span class="s">${esc(filtrosTxt() || 'con eventos, sin venta interna')}</span></div>
    <button type="button" class="kpi" data-ir="hora" data-h="${HORAS[ih]}" title="Ir a la celda más fuerte de esa hora"><span class="r">Hora pico</span><span class="v">${hh(HORAS[ih])}</span><span class="s">${pc(porHora[ih] / tot)} de la venta</span></button>
    <button type="button" class="kpi" data-ir="dia" data-w="${wMax}" title="Ir a su hora más fuerte"><span class="r">Mejor día</span><span class="v">${DIAS_L[wMax]}</span><span class="s">S/ ${k(prom[wMax] || 0)} por día · flojo: ${DIAS_L[wMin]}</span></button>
    <div class="kpi"><span class="r">Mediodía · noche</span><span class="v">${pc(mediodia / tot)} · ${pc(1 - mediodia / tot)}</span><span class="split"><i style="width:${(100 * mediodia / tot).toFixed(1)}%"></i><i></i></span></div>
    <div class="kpi"><span class="r">Contra ${ref === 'otro' ? S.otro + ' semanas antes' : REF_NOM[ref]}</span><span class="v ${vs >= 0 ? 'verde' : 'rojo'}">${isFinite(vs) ? (vs >= 0 ? '▲ ' : '▼ ') + pc(Math.abs(vs)) : '—'}</span><span class="s">${isFinite(vs) ? 'las mismas horas, cada día' : 'sin datos para comparar'}</span></div>
    <div class="kpi"><span class="r">Gasto por persona</span><span class="v">S/ ${(pax ? cli / pax : 0).toFixed(0)}</span><span class="s">${fn(mesas)} mesas · ${fn(pax)} personas</span></div>`;
}

// ── Colores ──────────────────────────────────────────────────────────────
const ESC_V = '<span class="esc"><i style="background:var(--c0)"></i><i style="background:var(--c1)"></i><i style="background:var(--c2)"></i><i style="background:var(--c3)"></i><i style="background:var(--c4)"></i><i style="background:var(--c5)"></i></span>';
const ESC_D = '<span class="esc"><i style="background:color-mix(in srgb, var(--neg) 90%, var(--bg-card))"></i><i style="background:color-mix(in srgb, var(--neg) 35%, var(--bg-card))"></i><i style="background:var(--c1)"></i><i style="background:color-mix(in srgb, var(--pos) 35%, var(--bg-card))"></i><i style="background:color-mix(in srgb, var(--pos) 90%, var(--bg-card))"></i></span>';
const colorValor = (v, max) => (!isFinite(v) || v <= 0 ? 'var(--vacio)' : `var(--c${Math.min(5, Math.floor((v / max) * 5.999))})`);
function colorDif(v, ref, chica) {
  if (Math.max(isFinite(v) ? v : 0, isFinite(ref) ? ref : 0) < chica) return 'var(--vacio)';
  if (!isFinite(ref) || ref <= 0) return isFinite(v) && v > 0 ? 'var(--c1)' : 'var(--vacio)';
  const d = Math.max(-1, Math.min(1, (v - ref) / ref)), p = Math.round(Math.abs(d) * 85) + 10;
  return `color-mix(in srgb, ${d >= 0 ? 'var(--pos)' : 'var(--neg)'} ${p}%, var(--bg-card))`;
}
function umbralChico(vals) { const o = vals.filter((v) => isFinite(v) && v > 0).sort((a, b) => a - b); return o.length ? 0.3 * o[Math.floor(o.length * 0.75)] : 0; }
const difTxt = (v, ref, chica) => (Math.max(v || 0, ref || 0) >= chica && ref > 0 ? `${v >= ref ? '+' : '−'}${Math.round(Math.abs(v / ref - 1) * 100)}%` : '');
const comparando = () => S.comp !== 'nada' && disponible(S.comp);
const refTexto = () => (S.comp === 'otro' ? `${S.otro} semanas antes` : REF_NOM[S.comp]);

// ── «Cuándo se vende»: el mapa de horas ──────────────────────────────────
let GEO = null;
const numFranja = (i) => `<span class="fnum" style="background:${FCOL[i]}">${i + 1}</span>`;
function contornos(cs, L, T, cw, filaH, dias) {
  // El contorno de cada franja sobre las filas que toca; media fila si
  // empieza o termina a la media hora. En la esquina de cada recuadro, el
  // número de su franja (el de su ficha): en «Día por día» una franja de
  // días de la semana se dibuja una vez por cada uno de esos días, y sin el
  // número diez recuadros parecían diez franjas.
  let s = '';
  if (!S.verFranjas) return s;
  const marcas = [], puestas = [];
  S.franjas.forEach((f, fi) => {
    const set = new Set(diasDe(f, dias)), cub = cs.map((c) => c.dias.some((d) => set.has(d)));
    const act = S.factiva === f.id, apagada = S.factiva && !act;
    const filas = HORAS.map((h, i) => [i, enFranja(f, h * 2), enFranja(f, h * 2 + 1)]).filter(([, a, b]) => a || b);
    if (!filas.length) return;
    const pri = filas[0], ult = filas[filas.length - 1];
    const y0 = T + pri[0] * filaH + (pri[1] ? 0 : filaH / 2), y1 = T + ult[0] * filaH + (ult[2] ? filaH : filaH / 2);
    let j = 0;
    while (j < cs.length) {
      if (!cub[j]) { j++; continue; }
      let j2 = j; while (j2 + 1 < cs.length && cub[j2 + 1]) j2++;
      // Cada franja un poco más adentro que la anterior, sin comerse una columna angosta.
      const ins = 1 + fi * Math.min(2, Math.max(0, (cw - 8) / 8));
      s += `<rect x="${L + j * cw + ins}" y="${y0 + ins}" width="${Math.max(2, (j2 - j + 1) * cw - 2 * ins)}" height="${Math.max(4, y1 - y0 - 2 * ins)}" rx="4" fill="none" style="stroke:${FCOL[fi]}${apagada ? ';opacity:.35' : ''}" stroke-width="${act ? 3.4 : 2.2}" pointer-events="none"/>`;
      // El número, arriba a la izquierda; si otro ya ocupa ese rincón, al lado.
      let x = L + j * cw + ins + 2;
      const y = y0 + ins + 2;
      while (puestas.some(([px, py]) => Math.abs(px - x) < 13 && Math.abs(py - y) < 13)) x += 13;
      puestas.push([x, y]);
      marcas.push(`<g pointer-events="none"${apagada ? ' opacity=".35"' : ''}><rect x="${x}" y="${y}" width="12" height="12" rx="3" style="fill:${FCOL[fi]}"/><text class="fr-num" x="${x + 6}" y="${y + 9.3}" text-anchor="middle">${fi + 1}</text></g>`);
      j = j2 + 1;
    }
  });
  return s + marcas.join('');
}
function cabeceraCuando() {
  const largo = DIAS_R.length > 45;
  const izq = `${seg('modo', [['semana', 'Semana tipo'], ['dia', 'Día por día'], ['mes', 'Mes por mes']], S.modo, largo ? {} : { mes: 'Con rangos de más de un mes' })}
    ${S.modo !== 'dia' ? seg('celda', [['prom', 'Promedio por día'], ['total', 'Total']], S.celda) : ''}
    ${comparando() ? seg('mostrar', [['mapa', 'Coloreado'], ['lado', 'Lado a lado']], S.mostrar) : ''}
    <button type="button" class="puntos" id="menu" title="Dibujo y cifras" aria-label="Dibujo y cifras">⋯</button>
    <label class="interruptor" title="Ver las franjas en el mapa; con esto prendido, arrastrar crea una o redibuja la elegida"><input type="checkbox" id="verfranjas" ${S.verFranjas ? 'checked' : ''}><span class="pista" aria-hidden="true"></span>Franjas</label>
    ${S.menu ? `<div class="mini-pop" id="minipop"><div><span class="rot">Dibujo</span> ${seg('forma', [['mosaico', 'Mosaico'], ['puntos', 'Puntos']], S.forma)}</div><label class="sw"><input type="checkbox" id="cifras" ${S.cifras ? 'checked' : ''}> Escribir la cifra en cada celda</label></div>` : ''}`;
  const fichas = S.verFranjas ? S.franjas.map((f, i) => `<span class="fchip${S.factiva === f.id ? ' on' : ''}" style="border-color:${FCOL[i]}"><button type="button" class="fnom" data-factiva="${f.id}" title="${esc(describir(f))} · tocala y arrastrá sobre el mapa para redibujarla">${numFranja(i)}${esc(f.nombre)}</button><button type="button" class="fx" data-fquitar="${f.id}" aria-label="Quitar ${esc(f.nombre)}" title="Quitar">✕</button></span>`).join('') : '';
  // El interruptor va con los controles del mapa (a la izquierda, donde sobra
  // lugar); acá, sólo las fichas: con cuatro, el renglón no se parte.
  const der = fichas
    + (S.franjas.length ? `<button type="button" class="link" id="ir-comp" title="La comparación de las ${S.franjas.length} franjas, en la tarjeta de abajo">Comparar ↓</button>` : '');
  $('gcab').innerHTML = `<div class="izq">${izq}</div><div class="der">${der}</div>`;
}
function mapaHoras() {
  const cs = celdas(columnas()), cmp = comparando();
  // La leyenda primero: si ocupa dos renglones, el mapa se mide con lo que queda.
  $('ley').innerHTML = (cmp ? `${ESC_D}<span>contra ${esc(refTexto())}: rojo menos, verde más · gris: muy chica para comparar</span>` : `${ESC_V}<span>${esc(MED[S.medida][0].toLowerCase())}${S.modo !== 'dia' ? (S.celda === 'prom' ? ', promedio por día' : ', total') : ''}: de menos a más</span>`)
    + '<span><i class="pt"></i> eventos en la celda</span>' + (S.modo === 'dia' ? '<span><span class="fer">*</span> feriado</span>' : '') + (S.modo === 'mes' ? '<span>* mes incompleto</span>' : '')
    + '<span>al margen: % de la venta de cada hora · total de cada columna</span>'
    + (S.verFranjas ? `<span class="ley-fr">recuadros: tus franjas, con el número y el color de su ficha${S.modo === 'dia' ? ' · en «Día por día» una franja de días de la semana se dibuja en cada uno de esos días' : ''} · ${S.factiva ? `arrastrá para redibujar «${esc((S.franjas.find((f) => f.id === S.factiva) || {}).nombre || '')}»` : S.franjas.length < 4 ? 'arrastrá para crear una · tocá una ficha para redibujarla' : 'hasta 4: quitá una para crear otra · tocá una ficha para redibujarla'}</span>` : '');
  const cont = $('svgw'), Wc = Math.max(420, cont.clientWidth - 2), Hc = Math.max(200, cont.clientHeight - 2);
  const L = 44, R = 60, T = 4, B = 40, n = cs.length;
  const filaH = Math.max(15, Math.min(26, (Hc - T - B) / HORAS.length));
  const cw = Math.max(S.modo === 'dia' ? 15 : 30, (Wc - L - R) / n), W = L + R + cw * n, H = T + HORAS.length * filaH + B;
  GEO = { L, T, cw, filaH, n, cols: cs };
  const max = Math.max(1e-9, ...cs.flatMap((c) => c.h.map((x) => (isFinite(x.v) ? x.v : 0))));
  const porHora = HORAS.map((_, i) => cs.reduce((s, c) => s + (c.h[i].a.venta || 0) * divisorDe(c), 0));
  const porCol = cs.map((c) => c.h.reduce((s, x) => s + x.a.venta, 0) * divisorDe(c));
  const totH = porHora.reduce((a, b) => a + b, 0) || 1, mh = Math.max(...porHora, 1), mc = Math.max(...porCol, 1);
  const refs = cmp ? cs.map((c) => c.h.map((x) => refCelda(S.comp, c.dias, x.h, divisorDe(c)))) : null;
  const chica = umbralChico(cs.flatMap((c) => c.h.map((x) => x.v)));
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" id="svgmapa" role="img" aria-label="Mapa por hora">`;
  HORAS.forEach((h, i) => {
    const y = T + i * filaH;
    s += `<text class="c-t" x="${L - 6}" y="${y + filaH / 2 + 3.5}" text-anchor="end">${hh(h)}</text>`;
    if (porHora[i] < 1) { s += `<text class="cerrado" x="${L + (W - L - R) / 2}" y="${y + filaH / 2 + 3.5}" text-anchor="middle">sin ventas a esta hora</text>`; return; }
    cs.forEach((c, j) => {
      const x = c.h[i], cx = L + j * cw, ref = cmp ? refs[j][i] : NaN, sel = S.sel && S.sel.col === c.id && S.sel.h === h;
      if (S.forma === 'puntos' && !cmp) {
        s += `<rect class="cel${sel ? ' sel' : ''}" x="${cx + 1}" y="${y + 1}" width="${Math.max(1, cw - 2)}" height="${filaH - 2}" rx="3" style="fill:var(--bg-card)" data-j="${j}" data-i="${i}"/>`;
        if (x.v > 0) s += `<circle cx="${cx + cw / 2}" cy="${y + filaH / 2}" r="${(1.5 + Math.min(filaH / 2 - 2, cw / 2 - 2) * Math.sqrt(x.v / max)).toFixed(1)}" style="fill:var(--c4)" pointer-events="none"/>`;
      } else s += `<rect class="cel${sel ? ' sel' : ''}" x="${cx + 1}" y="${y + 1}" width="${Math.max(1, cw - 2)}" height="${filaH - 2}" rx="3" style="fill:${cmp ? colorDif(x.v, ref, chica) : colorValor(x.v, max)}" data-j="${j}" data-i="${i}"/>`;
      if (x.a.raro > 0.5 && x.v > 0 && cw > 18) s += `<circle cx="${cx + cw - 5}" cy="${y + 5}" r="2.3" style="fill:var(--warning)" pointer-events="none"/>`;
      if (S.cifras && isFinite(x.v) && x.v > 0 && cw > 28) s += `<text class="c-n" x="${cx + cw / 2}" y="${y + filaH / 2 + 3.5}" text-anchor="middle" style="fill:${!cmp && x.v / max > 0.5 && S.forma === 'mosaico' ? 'var(--bg-card)' : 'var(--text-primary)'}">${cmp ? difTxt(x.v, ref, chica) : (MED[S.medida][2] ? k(x.v) : MED[S.medida][1](x.v))}</text>`;
    });
    const bw = (R - 26) * porHora[i] / mh;
    s += `<rect class="mar${porHora[i] === mh ? ' pico' : ''}" x="${W - R + 6}" y="${y + filaH * 0.28}" width="${bw}" height="${filaH * 0.44}" rx="2"/><text class="mar-t" x="${W - R + 9 + bw}" y="${y + filaH / 2 + 3.5}">${pc(porHora[i] / totH)}</text>`;
  });
  s += contornos(cs, L, T, cw, filaH, DIAS_R);
  const yb = T + HORAS.length * filaH;
  cs.forEach((c, j) => {
    const cx = L + j * cw + cw / 2, on = S.sel && S.sel.col === c.id;
    const muestra = S.modo !== 'dia' || cw > 22 || (n > 40 ? dow(c.id) === 0 : j % 2 === 0) || (on && n <= 40);
    if (muestra) s += `<text class="c-t${c.fer ? ' fer' : ''}${on ? ' on' : ''}" x="${cx}" y="${yb + 12}" text-anchor="middle">${n > 40 && S.modo === 'dia' ? fecha(c.id) : c.rot}${c.fer ? '*' : ''}</text>`;
    const bh = 16 * porCol[j] / mc;
    s += `<rect class="mar" x="${cx - Math.min(13, cw / 3)}" y="${yb + 34 - bh}" width="${Math.min(26, cw / 1.5)}" height="${bh}" rx="2"><title>${soles(porCol[j])}</title></rect>`;
  });
  s += `<text class="mar-t" x="${L - 6}" y="${yb + 32}" text-anchor="end">total</text><rect id="arrastre" x="0" y="0" width="0" height="0" rx="4" fill="none" style="stroke:var(--accent-deep)" stroke-dasharray="4 3" stroke-width="2" pointer-events="none"/></svg>`;
  if (W > cont.clientWidth + 1) {
    // Deslizable: las horas, fijas a la izquierda (una capa con el fondo de la tarjeta encima de las de la figura).
    let e = `<svg width="${L}" height="${H}" style="display:block"><rect width="${L}" height="${H}" style="fill:var(--bg-card)"/>`;
    HORAS.forEach((h, i) => { e += `<text class="c-t" x="${L - 6}" y="${T + i * filaH + filaH / 2 + 3.5}" text-anchor="end">${hh(h)}</text>`; });
    e += `<text class="mar-t" x="${L - 6}" y="${yb + 32}" text-anchor="end">total</text></svg>`;
    cont.innerHTML = `<div style="width:max-content"><div style="position:sticky;left:0;width:${L}px;height:0;z-index:2">${e}</div>${s}</div>`;
    const j = cs.findIndex((c) => S.sel && c.id === S.sel.col);
    cont.scrollLeft = j >= 0 ? Math.max(0, L + j * cw - cont.clientWidth / 2) : W;
  } else cont.innerHTML = s;
  return cs;
}
function ladoALado() {
  const lista = [{ id: 'este', nom: 'Este período', sub: rangoTxt() }];
  for (const r of ['normal', 'ap', 'otro']) {
    if (!S.paneles.has(r) || !disponible(r)) continue;
    const corr = r === 'normal' ? -56 : corrimiento(r);
    lista.push({ id: r, nom: r === 'normal' ? 'Lo normal' : r === 'ap' ? 'Año pasado' : `${S.otro} semanas antes`, sub: r === 'normal' ? 'mediana de las 8 semanas anteriores' : `${fecha(mas(INI, corr))} – ${fecha(mas(FIN, corr))}`, ref: r });
  }
  const cols = columnas('semana');
  const pan = lista.map((p) => ({ ...p, m: cols.map((c) => HORAS.map((h) => { const dv = S.celda === 'total' ? 1 : Math.max(1, c.dias.length); return p.id === 'este' ? valor(div(agg(c.dias, h), dv)) : refCelda(p.ref, c.dias, h, dv); })) }));
  const max = Math.max(1e-9, ...pan.flatMap((p) => p.m.flat().filter((v) => isFinite(v))));
  $('ley').innerHTML = `${ESC_V}<span>semana tipo · ${esc(MED[S.medida][0].toLowerCase())} · la misma escala en todos los paneles</span><span>las franjas se dibujan en cada período</span><span>para tocar una celda, volvé a «Coloreado»</span>`;
  const cont = $('svgw'), Wc = Math.max(420, cont.clientWidth - 2), Hc = Math.max(200, cont.clientHeight - 4);
  const porFila = Math.min(4, pan.length), Wp = (Wc - (porFila - 1) * 12) / porFila;
  const L = 40, T = 2, filaH = Math.max(13, Math.min(24, (Hc - 40) / HORAS.length)), cw = (Wp - L - 4) / 7, H = T + HORAS.length * filaH + 16;
  cont.innerHTML = `<div class="paneles" style="grid-template-columns:repeat(${porFila}, minmax(0, 1fr))">${pan.map((p, pi) => {
    let s = `<svg width="${Wp}" height="${H}" viewBox="0 0 ${Wp} ${H}">`;
    HORAS.forEach((h, i) => { const y = T + i * filaH; s += `<text class="c-t" x="${L - 4}" y="${y + filaH / 2 + 3.5}" text-anchor="end">${hh(h)}</text>`;
      cols.forEach((c, j) => { const v = p.m[j][i]; s += `<rect x="${L + j * cw + 1}" y="${y + 1}" width="${cw - 2}" height="${filaH - 2}" rx="2" style="fill:${colorValor(v, max)}"><title>${esc(p.nom)} · ${DIAS_PL[j]} ${hh(h)}: ${isFinite(v) ? MED[S.medida][1](v) : '—'}</title></rect>`;
        if (S.cifras && isFinite(v) && v > 0 && cw > 30) s += `<text class="c-n" x="${L + j * cw + cw / 2}" y="${y + filaH / 2 + 3.5}" text-anchor="middle" style="fill:${v / max > 0.5 ? 'var(--bg-card)' : 'var(--text-primary)'}">${MED[S.medida][2] ? k(v) : MED[S.medida][1](v)}</text>`; }); });
    s += contornos(cols, L, T, cw, filaH, DIAS_R);
    cols.forEach((c, j) => { s += `<text class="c-t" x="${L + j * cw + cw / 2}" y="${H - 3}" text-anchor="middle">${c.rot}</text>`; });
    const d = pi ? contra(p.ref) : NaN;
    return `<div><div class="panel-t"><span><b>${esc(p.nom)}</b> · <span class="gris">${esc(p.sub)}</span></span><span>${pi ? `<span class="${d >= 0 ? 'verde' : 'rojo'}">este período ${d >= 0 ? '▲' : '▼'} ${pc(Math.abs(d))}</span>` : ''}</span></div>${s}</svg></div>`;
  }).join('')}</div>`;
  GEO = null;
  $('gcab').querySelector('.der').innerHTML = `<span class="rot">Paneles</span><span class="chips">${[['normal', 'Lo normal'], ['ap', 'Año pasado'], ['otro', 'Otro período']].map(([r, t]) => `<button type="button" data-panel="${r}" class="${S.paneles.has(r) ? 'on' : ''}" ${disponible(r) ? '' : 'disabled title="No hay datos cargados para ese período"'}>${t}</button>`).join('')}</span>`;
}

// ── «Qué se vende a cada hora»: platos, grupos o áreas ───────────────────
function claveItem(l, por = S.por) { const p = PRODS[l[L_PROD]]; return por === 'platos' ? p.nombre : por === 'grupos' ? p.grupo : p.area; }
const medItems = () => (MED[S.medida][2] ? S.medida : 'venta');
const nColsItems = () => (S.colsVer === 'hora' ? HORAS.length : 7);
function sumaItems(dias, med = medItems()) {
  const m = new Map(), u = new Map(), nC = nColsItems();
  for (const d of dias) for (const f of PORDIA.get(d) || []) {
    const j = S.colsVer === 'hora' ? HORAS.indexOf(Math.floor(f.min / 60)) : dow(d); if (j < 0) continue;
    for (const l of f.lin) { const kk = claveItem(l); let a = m.get(kk); if (!a) { a = new Array(nC).fill(0); m.set(kk, a); } a[j] += med === 'venta' ? l[L_VENTA] : med === 'cant' ? l[L_CANT] : l[L_DESC]; u.set(kk, (u.get(kk) || 0) + l[L_CANT]); }
  }
  return { m, u };
}
function divisoresItems() { return S.colsVer === 'hora' ? HORAS.map(() => (S.celda === 'total' ? 1 : DIAS_R.length)) : DIAS.map((_, w) => (S.celda === 'total' ? 1 : Math.max(1, DIAS_R.filter((d) => dow(d) === w).length))); }
const colsItems = () => (S.colsVer === 'hora' ? HORAS.map(hh) : DIAS);
function itemsActuales() {
  const { m, u } = sumaItems(DIAS_R), dv = divisoresItems();
  return [...m.entries()].map(([nombre, v]) => ({ nombre, v: v.map((x, j) => x / dv[j]), t: v.reduce((a, b) => a + b, 0), u: u.get(nombre) || 0 })).filter((x) => Math.abs(x.t) > 0.005).sort((a, b) => b.t - a.t);
}
function refItems(items) {
  if (!comparando()) return null;
  const dv = divisoresItems();
  const sets = S.comp === 'normal' ? SEMANAS.map((s) => sumaItems(correr(DIAS_R, -7 * s)).m) : [sumaItems(correr(DIAS_R, corrimiento(S.comp))).m];
  return new Map(items.map((x) => [x.nombre, x.v.map((_, j) => mediana(sets.map((m) => ((m.get(x.nombre) || [])[j] || 0) / dv[j])))]));
}
function cabeceraQue() {
  const notas = { platos: 'Cada fila contra sí misma: su perfil horario', grupos: 'La mezcla de cada hora (barras al 100 %)', areas: 'La carga de cada estación: una sola escala' };
  $('gcab').innerHTML = `<div class="izq">${seg('por', [['platos', 'Platos'], ['grupos', 'Grupos'], ['areas', 'Áreas']], S.por)}
    <span class="rot">Columnas</span>${seg('colsVer', [['hora', 'Hora'], ['dow', 'Día de la semana']], S.colsVer)}
    ${S.por !== 'grupos' ? seg('celda', [['prom', 'Promedio por día'], ['total', 'Total']], S.celda) : ''}
    <button type="button" class="puntos" id="menu" title="Cifras" aria-label="Cifras">⋯</button>
    ${S.menu ? `<div class="mini-pop" id="minipop"><label class="sw"><input type="checkbox" id="cifras" ${S.cifras ? 'checked' : ''}> Escribir la cifra en cada celda</label></div>` : ''}</div>
    <div class="der"><span class="fi-de">${notas[S.por]}${delPedido(S.medida) ? ' · se muestra la venta' : ''}</span></div>`;
}
function mapaFilas(items, porFila) {
  // Platos (porFila = true: cada fila contra sí misma) o áreas (una sola escala).
  const ref = refItems(items), cols = colsItems(), med = medItems();
  $('ley').innerHTML = (ref ? `${ESC_D}<span>cada celda contra ${esc(refTexto())}</span>` : `${ESC_V}<span>${porFila ? 'de menos a más, cada fila contra sí misma: muestra a qué hora vende cada plato, no cuánto' : `${esc(MED[med][0].toLowerCase())}, una sola escala para todas: la carga de cada estación`}</span>`) + '<span>al margen: su parte del total · clic: su ficha</span>';
  const cont = $('svgw'), W = Math.max(420, cont.clientWidth - 2);
  const L = 180, R = 64, T = 18, filaH = 21, n = cols.length, cw = (W - L - R) / n;
  const filas = [];
  if (porFila) {
    const buenos = items.filter((x) => x.u >= MIN_UNID), flojos = items.filter((x) => x.u < MIN_UNID);
    (S.todos ? buenos : buenos.slice(0, 25)).forEach((x) => filas.push({ x }));
    // El elegido (un salto desde «Análisis de platos») se ve aunque no esté entre los 25.
    if (!S.todos && S.item && !filas.some((r) => r.x.nombre === S.item)) { const x = buenos.find((z) => z.nombre === S.item); if (x) filas.push({ x }); }
    if (buenos.length > 25) filas.push({ boton: 'todos', txt: S.todos ? 'Sólo los 25 que más venden' : `Ver los ${buenos.length} con al menos ${MIN_UNID} unidades` });
    if (flojos.length) {
      const chicos = S.chicos || flojos.some((z) => z.nombre === S.item);
      filas.push({ boton: 'chicos', txt: chicos ? `Ocultar los ${flojos.length} con poca venta` : `${flojos.length} platos con menos de ${MIN_UNID} unidades (el color no es confiable)` });
      if (chicos) flojos.forEach((x) => filas.push({ x, flojo: true }));
    }
  } else items.forEach((x) => filas.push({ x }));
  const H = T + filas.length * filaH + 4;
  const maxG = Math.max(1e-9, ...items.flatMap((x) => x.v)), mt = Math.max(1e-9, ...items.map((x) => x.t)), tot = items.reduce((a, x) => a + x.t, 0) || 1;
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Qué se vende a cada hora" class="clic">`;
  cols.forEach((c, j) => { s += `<text class="c-t" x="${L + j * cw + cw / 2}" y="12" text-anchor="middle">${c}</text>`; });
  filas.forEach((r, i) => {
    const y = T + i * filaH;
    if (r.boton) { s += `<text class="c-t boton" x="${L - 8}" y="${y + filaH / 2 + 3.5}" text-anchor="end" data-boton="${r.boton}">${esc(r.txt)}</text>`; return; }
    const x = r.x, on = S.item === x.nombre, mf = porFila ? Math.max(1e-9, ...x.v) : maxG;
    const chica = umbralChico(porFila ? x.v : items.flatMap((z) => z.v));
    s += `<g class="fila-item" data-item="${esc(x.nombre)}"><text class="c-t${on ? ' on' : ''}${r.flojo ? ' flojo' : ''}" x="${L - 8}" y="${y + filaH / 2 + 3.5}" text-anchor="end">${esc(x.nombre.length > 28 ? x.nombre.slice(0, 27) + '…' : x.nombre)}</text>`;
    x.v.forEach((v, j) => {
      const rv = ref ? ref.get(x.nombre)[j] : NaN;
      const fill = ref ? colorDif(v, rv, chica) : colorValor(v, mf);
      s += `<rect class="cel${on ? ' sel' : ''}" x="${L + j * cw + 1}" y="${y + 1}" width="${cw - 2}" height="${filaH - 2}" rx="3" style="fill:${fill}${r.flojo ? ';opacity:.45' : ''}"><title>${esc(x.nombre)} · ${cols[j]}: ${MED[med][1](v)}${ref && isFinite(rv) ? ` · ${refTexto()}: ${MED[med][1](rv)}` : ''}</title></rect>`;
      if (S.cifras && v > 0.05 && cw > 30) s += `<text class="c-n" x="${L + j * cw + cw / 2}" y="${y + filaH / 2 + 3.5}" text-anchor="middle" style="fill:${!ref && v / mf > 0.5 ? 'var(--bg-card)' : 'var(--text-primary)'}">${ref ? difTxt(v, rv, chica) : k(v)}</text>`;
    });
    const bw = (R - 28) * x.t / mt;
    s += `<rect class="mar" x="${W - R + 6}" y="${y + 6}" width="${Math.max(0, bw)}" height="${filaH - 12}" rx="2"/><text class="mar-t" x="${W - R + 9 + Math.max(0, bw)}" y="${y + filaH / 2 + 3.5}">${pc(x.t / tot)}</text></g>`;
  });
  cont.innerHTML = s + '</svg>';
  // El elegido, a la vista.
  const sel = cont.querySelector('.fila-item text.on');
  if (sel) { const r = sel.getBoundingClientRect(), rc = cont.getBoundingClientRect(); if (r.top < rc.top || r.bottom > rc.bottom) cont.scrollTop += r.top - rc.top - rc.height / 2; }
}
function barrasGrupos(items) {
  const cols = colsItems(), n = cols.length, med = medItems();
  const totCol = cols.map((_, j) => items.reduce((a, x) => a + Math.max(0, x.v[j]), 0));
  // Pálida: menos del 5 % de la columna más grande; ahí un 100 % no dice nada.
  const ref = comparando() ? refItems(items) : null, chica = 0.05 * Math.max(...totCol);
  $('ley').innerHTML = items.map((x, i) => `<span data-item="${esc(x.nombre)}" class="ley-it"><i class="sw2" style="background:${SCOL(i)}"></i>${esc(x.nombre)}</span>`).join('') + `<span>· arriba: el total de cada columna · pálida: tan poca venta que el % no dice nada${ref ? ` · al pasar el cursor, contra ${esc(refTexto())}` : ''}</span>`;
  const cont = $('svgw'), W = Math.max(420, cont.clientWidth - 2), Hc = Math.max(200, cont.clientHeight - 4);
  const L = 40, R = 10, T = 18, B = 22, cw = (W - L - R) / n, bw = Math.min(54, cw * 0.66), H = Hc, y0 = H - B, alto = H - T - B;
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Mezcla de cada hora" class="clic">`;
  [0, 0.25, 0.5, 0.75, 1].forEach((p) => { const y = y0 - alto * p; s += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" style="stroke:var(--line-soft)"/><text class="mar-t" x="${L - 6}" y="${y + 3}" text-anchor="end">${pc(p)}</text>`; });
  cols.forEach((c, j) => {
    const cx = L + j * cw + cw / 2;
    s += `<text class="c-t" x="${cx}" y="${H - 6}" text-anchor="middle">${c}</text>`;
    if (totCol[j] <= 0.5) { s += `<text class="cerrado" x="${cx}" y="${y0 - 6}" text-anchor="middle">—</text>`; return; }
    let acc = 0;
    const palida = totCol[j] < chica;
    items.forEach((x, i) => {
      const v = Math.max(0, x.v[j]); if (v <= 0) return;
      const p = v / totCol[j], h = alto * p, y = y0 - alto * acc - h;
      let tip = `${esc(x.nombre)} · ${c}: ${pc(p)} (${MED[med][1](v)})`;
      if (ref) { const rt = items.reduce((a, z) => a + Math.max(0, (ref.get(z.nombre) || [])[j] || 0), 0), rp = rt ? ((ref.get(x.nombre) || [])[j] || 0) / rt : NaN; if (isFinite(rp)) tip += ` · ${refTexto()}: ${pc(rp)} (${p >= rp ? '+' : '−'}${Math.abs((p - rp) * 100).toFixed(1)} pp)`; }
      s += `<rect class="seg-b" x="${cx - bw / 2}" y="${y}" width="${bw}" height="${Math.max(0, h - 0.6)}" style="fill:${SCOL(i)};${palida ? 'opacity:.22' : S.item && S.item !== x.nombre ? 'opacity:.35' : ''}" data-item="${esc(x.nombre)}"><title>${tip}</title></rect>`;
      if (h > 14 && bw > 30 && !palida) s += `<text class="c-n" x="${cx}" y="${y + h / 2 + 3.5}" text-anchor="middle" style="fill:var(--bg-card)">${Math.round(p * 100)}%</text>`;
      acc += p;
    });
    s += `<text class="mar-t" x="${cx}" y="${T - 5}" text-anchor="middle">${MED[med][2] && med !== 'venta' ? fn(totCol[j]) : k(totCol[j])}</text>`;
    if (palida) s += `<text class="cerrado" x="${cx}" y="${y0 - alto / 2}" text-anchor="middle">poca venta</text>`;
  });
  cont.innerHTML = s + '</svg>';
}
function graficoQue() {
  if (S.por === 'areas' && S.medida === 'venta' && !S.areasAuto) { S.areasAuto = true; S.medida = 'cant'; if (!S.areasUnid) { S.areasUnid = true; aviso('Áreas abre en unidades: la carga de cada estación. Podés volver a Venta en «Medir».'); } general(); }
  if (S.por !== 'areas' && S.areasAuto) { const auto = S.areasAuto === true; S.areasAuto = false; if (auto && S.medida === 'cant') { S.medida = 'venta'; general(); } }
  cabeceraQue();
  const items = itemsActuales();
  if (!S.item || !items.some((x) => x.nombre === S.item)) S.item = S.por === 'grupos' ? null : items[0]?.nombre ?? null;
  if (S.por === 'grupos') barrasGrupos(items); else mapaFilas(items, S.por === 'platos');
  GEO = null;
  return items;
}

// ── El detalle de lo elegido ─────────────────────────────────────────────
function pill(v, txt) { return isFinite(v) ? `<span class="pill ${Math.abs(v) < 0.02 ? 'n' : v > 0 ? 'pos' : 'neg'}">${Math.abs(v) < 0.02 ? (txt ? '≈ ' + txt.replace('vs ', '') : '≈ igual') : `${v > 0 ? '▲' : '▼'} ${pc(Math.abs(v))} ${txt}`.trim()}</span>` : ''; }
function tira(vals, v, fmt) {
  const W = 300, H = 44, all = [...vals, v].filter((x) => isFinite(x)); if (!all.length) return '';
  const mx = Math.max(...all, 1), px = (x) => 8 + (W - 16) * x / mx, med = mediana(vals);
  let s = `<svg class="tira" viewBox="0 0 ${W} ${H}"><line x1="8" x2="${W - 8}" y1="23" y2="23" style="stroke:var(--border)"/>`;
  vals.forEach((x) => { if (isFinite(x)) s += `<circle cx="${px(x)}" cy="23" r="4" style="fill:var(--text-muted)"/>`; });
  if (isFinite(med)) s += `<line x1="${px(med)}" x2="${px(med)}" y1="13" y2="33" style="stroke:var(--text-secondary)" stroke-width="1.5"/>`;
  return s + `<circle cx="${px(v)}" cy="23" r="6" style="fill:var(--accent)"/><text x="${px(v)}" y="9" text-anchor="middle" style="font-size:10px;fill:var(--accent-deep);font-weight:700">esta</text><text x="8" y="${H - 1}" style="font-size:10px;fill:var(--text-secondary)">0</text><text x="${W - 8}" y="${H - 1}" text-anchor="end" style="font-size:10px;fill:var(--text-secondary)">${fmt(mx)}</text></svg>`;
}
function factores(dias, h) {
  // La celda partida en mesas × personas × gasto, y la operación (mesas a
  // la vez, tiempo, venta por hora de mesa). Mesa = pedido del local con
  // personas (ver ventas_horario.py).
  const n = Math.max(1, dias.length);
  let venta = 0, mesas = 0, pax = 0, cli = 0, aVez = 0; const durs = [], tasas = [];
  for (const d of dias) {
    const lst = PORDIA.get(d) || [];
    for (const f of lst) if (Math.floor(f.min / 60) === h) {
      venta += f.venta;
      if (f.mesa) { mesas++; pax += f.pax; cli += f.venta; if (f.o.dur != null) { durs.push(f.o.dur); if (f.o.dur >= 10) tasas.push(f.venta / (f.o.dur / 60)); } }
    }
    const loc = lst.filter((f) => f.mesa && f.o.dur != null); let mx = 0;
    for (let t = h * 60; t < h * 60 + 60; t += 5) { let c = 0; for (const f of loc) if (f.o.abre <= t && t < f.o.abre + f.o.dur) c++; if (c > mx) mx = c; }
    aVez += mx;
  }
  return { venta: venta / n, mesas: mesas / n, ppm: mesas ? pax / mesas : NaN, gasto: pax ? cli / pax : NaN, vpm: mesas ? cli / mesas : NaN, tiempo: mediana(durs), tasa: mediana(tasas), aVez: aVez / n };
}
function normales(dias, h) { const xs = SEMANAS.map((s) => factores(correr(dias, -7 * s), h)), o = {}; for (const kk of Object.keys(xs[0])) o[kk] = mediana(xs.map((x) => x[kk])); return { med: o, ventas: xs.map((x) => x.venta) }; }
const tiempoTxt = (m) => (isFinite(m) ? `${Math.floor(m / 60)} h ${String(Math.round(m % 60)).padStart(2, '0')}` : '—');
function cifra(rot, v, nv, fmt, sub = '') { return `<div class="cif"><span>${rot}</span><b>${isFinite(v) ? fmt(v) : '—'}</b>${isFinite(nv) && nv > 0 ? pill(v / nv - 1, '') : ''}<small>${isFinite(nv) ? 'normal ' + fmt(nv) : ''}${sub}</small></div>`; }
function fichaCelda(cs) {
  const c = cs.find((z) => z.id === S.sel.col); if (!c) return '<div class="nota">Tocá una celda.</div>';
  const i = HORAS.indexOf(S.sel.h); if (i < 0) return '<div class="nota">Tocá una celda.</div>';
  const x = c.h[i], dias = c.dias;
  const nombre = S.modo === 'dia' ? `${DIAS_L[dow(c.id)]} ${fecha(c.id)} · ${hh(x.h)}` : S.modo === 'mes' ? `${MES_L[Number(c.id.slice(5)) - 1]} · ${hh(x.h)}` : `${DIAS_PL[c.id]} · ${hh(x.h)}`;
  const de = S.modo === 'dia' ? (FER.has(c.id) ? 'feriado' : 'un día') : `${S.celda === 'prom' ? 'promedio por día de' : 'total de'} ${dias.length} días`;
  let h = `<div class="fi-cab"><div><div class="fi-nom">${esc(nombre[0].toUpperCase() + nombre.slice(1))}</div><div class="fi-de">${esc(de)}</div></div><button type="button" class="btn sec peq" id="ampliar">${S.ampliar ? 'Volver al mapa' : 'Ampliar'}</button></div>
    <div class="subtabs">${[['resumen', 'Resumen'], ['mesas', 'Mesas'], ['pedidos', 'Pedidos']].map(([v, r]) => `<button type="button" data-acc="tab" data-v="${v}" class="${S.tab === v ? 'on' : ''}">${r}</button>`).join('')}</div>`;
  const hayNormal = disponible('normal', dias), fa = factores(dias, x.h), nm = hayNormal ? normales(dias, x.h) : null, nf = nm ? nm.med : {};
  if (S.tab === 'resumen') {
    // Por prioridad: cuánto y contra qué → por qué → qué se vendió → el contexto.
    const ap = disponible('ap', dias) ? factores(correr(dias, -DIAS_AP), x.h).venta : NaN;
    const puesto = nm ? 1 + nm.ventas.filter((v) => v > fa.venta).length : NaN;
    const quien = S.modo === 'semana' ? DIAS_PL[c.id] : S.modo === 'dia' ? DIAS_PL[dow(c.id)] : 'semanas';
    const pl = new Map(); for (const d of dias) for (const f of PORDIA.get(d) || []) if (Math.floor(f.min / 60) === x.h) for (const l of f.lin) pl.set(l[L_PROD], (pl.get(l[L_PROD]) || 0) + l[L_VENTA]);
    const top = [...pl.entries()].sort((p, q) => q[1] - p[1]).slice(0, 5), tmax = top.length ? top[0][1] : 1, tsum = [...pl.values()].reduce((p, q) => p + q, 0) || 1;
    const porDia = dias.length > 1 ? dias.map((d) => [d, agg([d], x.h).venta]).sort((p, q) => (p[0] < q[0] ? 1 : -1)) : [];
    const pmax = Math.max(1, ...porDia.map((p) => p[1]));
    h += `<div class="fi-v"><b>${soles(fa.venta)}</b>${nm ? pill(fa.venta / nf.venta - 1, 'vs lo normal') : ''}${isFinite(ap) && ap > 0 ? pill(fa.venta / ap - 1, 'vs año pasado') : ''}</div>
      ${isFinite(puesto) ? `<div class="fi-de">La <b>${puesto}.ª</b> más alta de 9 ${quien} (esta y las 8 semanas anteriores).</div>` : ''}
      ${x.a.raro > 0.5 ? `<div class="nota">Incluye ${soles(x.a.raro)} de eventos${S.vinterna ? ' o venta interna' : ''}.</div>` : ''}
      ${fa.mesas > 0 ? `<div class="bl"><div class="bl-t">Por qué<span>mesas × personas × gasto, contra lo normal</span></div><div class="fact">${cifra('Mesas', fa.mesas, nf.mesas, (v) => v.toFixed(1))}<em>×</em>${cifra('Personas/mesa', fa.ppm, nf.ppm, (v) => v.toFixed(1))}<em>×</em>${cifra('Gasto/persona', fa.gasto, nf.gasto, (v) => 'S/ ' + v.toFixed(0))}</div></div>`
        : '<div class="nota">A esa hora no hubo mesas con personas registradas (evento, delivery o Rappi): no hay mesas × personas × gasto que partir.</div>'}
      ${top.length ? `<div class="bl"><div class="bl-t">Qué se vendió a esa hora</div><div class="mini">${top.map(([p, v]) => `<span title="${esc(PRODS[p].nombre)}">${esc(PRODS[p].nombre)}</span><span class="b"><i style="width:${(100 * v / tmax).toFixed(0)}%"></i></span><span class="d">${pc(v / tsum)}</span>`).join('')}</div></div>` : ''}
      ${nm ? `<div class="bl"><div class="bl-t">Contra las 8 semanas anteriores<span>venta por día</span></div>${tira(nm.ventas, fa.venta, soles)}<div class="fi-de">● esta · ○ cada semana · │ mediana ${soles(nf.venta)}</div></div>` : ''}
      ${porDia.length ? `<div class="bl"><div class="bl-t">Los ${porDia.length} días de esta celda<span>tocá uno para verlo</span></div><div class="dias-l">${porDia.slice(0, 31).map(([d, v]) => `<button type="button" data-dia="${d}">${DIAS[dow(d)]} ${fecha(d)}${FER.has(d) ? ' *' : ''}</button><span class="b"><i style="width:${(100 * v / pmax).toFixed(0)}%"></i></span><span class="d">${soles(v)}</span>`).join('')}</div></div>` : ''}
      <div class="acc"><button type="button" class="btn" id="franja-celda">Crear una franja con esta celda</button></div>`;
  } else if (S.tab === 'mesas') {
    // La operación: lo que no está ya en Resumen.
    h += `<div class="grid2">${cifra('Mesas a la vez, máx.', fa.aVez, nf.aVez, (v) => v.toFixed(1), ' · cada 5 min')}${cifra('Tiempo en la mesa', fa.tiempo, nf.tiempo, tiempoTxt, ' · mediana')}
      ${cifra('Venta por mesa', fa.vpm, nf.vpm, (v) => soles(v))}${cifra('Venta por hora de mesa', fa.tasa, nf.tasa, (v) => soles(v), ' · mediana')}</div>
      <div class="fi-de">Mesa = pedido del local con personas registradas; sin Rappi ni pedidos sin personas.</div>
      <div class="bl"><div class="bl-t">Mesas del salón<span>opcional</span></div><div class="g"><input class="num" type="number" min="1" max="300" id="salon" value="${S.salon ?? ''}" placeholder="p. ej. 30"><span class="fi-de">${S.salon ? `ocupación máxima ${pc(fa.aVez / S.salon)}${isFinite(nf.aVez) ? ` (normal ${pc(nf.aVez / S.salon)})` : ''}` : 'con el número de mesas, la ocupación'}</span></div></div>`;
  } else {
    const filas = []; for (const d of dias) for (const f of PORDIA.get(d) || []) if (Math.floor(f.min / 60) === x.h) filas.push(f);
    filas.sort((p, q) => (p.dia + String(p.min).padStart(4, '0')).localeCompare(q.dia + String(q.min).padStart(4, '0')));
    h += `<div class="fi-de">${filas.length} pedidos${dias.length > 1 ? ` en ${dias.length} días` : ''}${filas.length > 100 ? ' · los 100 primeros' : ''}</div><div><table class="ped"><thead><tr><th>Día</th><th>Abre</th><th>Canal</th><th class="n">Pers.</th><th class="n">Venta</th><th class="n">En mesa</th></tr></thead><tbody>
      ${filas.slice(0, 100).map((f) => `<tr><td>${fecha(f.dia)}</td><td>${hm(f.min)}</td><td>${esc(D.canales[f.o.canal] || 'Sin canal')}</td><td class="n">${f.pax || '—'}</td><td class="n">${soles(f.venta)}</td><td class="n">${f.mesa && f.o.dur != null ? Math.round(f.o.dur) + ' min' : '—'}</td></tr>`).join('')}</tbody></table></div>`;
  }
  return h;
}
function fichaItem(items) {
  if (S.por === 'grupos' && !S.item) return `<div class="fi-nom">La mezcla de cada hora</div><div class="fi-de">Tocá un grupo (en las barras o en la leyenda) para ver su ficha.</div>${items.slice(0, 8).map((x, i) => `<div class="mini"><span><i class="sw2" style="background:${SCOL(i)}"></i>${esc(x.nombre)}</span><span class="b"><i style="width:${(100 * x.t / (items[0]?.t || 1)).toFixed(0)}%;background:${SCOL(i)}"></i></span><span class="d">${pc(x.t / (items.reduce((a, z) => a + z.t, 0) || 1))}</span></div>`).join('')}`;
  const x = items.find((z) => z.nombre === S.item); if (!x) return '<div class="nota">Tocá una fila o una barra.</div>';
  const tot = items.reduce((a, z) => a + z.t, 0) || 1, porH = HORAS.map(() => 0), porW = DIAS.map(() => 0), uH = HORAS.map(() => 0), enF = S.franjas.map(() => 0); let u = 0, v = 0;
  const sumaDe = (dias) => { let s2 = 0; for (const d of dias) for (const f of PORDIA.get(d) || []) for (const l of f.lin) if (claveItem(l) === x.nombre) s2 += l[L_VENTA]; return s2; };
  const diasF = S.franjas.map((fr) => new Set(diasDe(fr)));
  for (const d of DIAS_R) for (const f of PORDIA.get(d) || []) for (const l of f.lin) if (claveItem(l) === x.nombre) {
    const i = HORAS.indexOf(Math.floor(f.min / 60)); if (i >= 0) { porH[i] += l[L_VENTA]; uH[i] += l[L_CANT]; } porW[dow(d)] += l[L_VENTA]; u += l[L_CANT]; v += l[L_VENTA];
    S.franjas.forEach((fr, fi) => { if (diasF[fi].has(d) && enFranja(fr, Math.floor(f.min / 30))) enF[fi] += l[L_VENTA]; });
  }
  const noche = porH.filter((_, i) => esNoche(HORAS[i])).reduce((a, b) => a + b, 0);
  const normal = disponible('normal') ? mediana(SEMANAS.map((s) => sumaDe(correr(DIAS_R, -7 * s)))) : NaN;
  const ap = disponible('ap') ? sumaDe(correr(DIAS_R, -DIAS_AP)) : NaN;
  const barras = (vals, rots, fmt) => { const W = 300, H = 62, mx = Math.max(...vals, 1e-9), bw = (W - 10) / vals.length; return `<svg class="barras" viewBox="0 0 ${W} ${H}">${vals.map((q, i) => `<rect x="${5 + i * bw + 2}" y="${H - 14 - (H - 22) * Math.max(0, q) / mx}" width="${Math.max(1, bw - 4)}" height="${(H - 22) * Math.max(0, q) / mx}" rx="2" style="fill:${q === mx ? 'var(--c5)' : 'var(--c2)'}"><title>${rots[i]}: ${fmt(q)}</title></rect><text x="${5 + i * bw + bw / 2}" y="${H - 3}" text-anchor="middle" style="font-size:9px;fill:var(--text-secondary)">${rots[i].replace(' pm', '').replace(' am', '')}</text>`).join('')}</svg>`; };
  const p = PRODS.find((z) => z.nombre === x.nombre), n = DIAS_R.length;
  const pico = uH.indexOf(Math.max(...uH));
  const subt = S.por === 'platos' && p ? `${p.grupo} › ${p.sub} · ${p.area}` : S.por === 'grupos' ? 'grupo de la carta' : 'área de producción';
  return `<div><div class="fi-nom">${esc(x.nombre)}</div><div class="fi-de">${esc(subt)}</div></div>
    ${S.por === 'platos' && x.u < MIN_UNID ? `<div class="nota">Vendió ${fn(x.u)} unidades en el rango: su perfil horario no es confiable.</div>` : ''}
    <div class="fi-v"><b>${soles(v)}</b>${pill(v / normal - 1, 'vs lo normal')}${pill(v / ap - 1, 'vs año pasado')}</div>
    <div class="grid2"><div class="cif"><span>Parte del total</span><b>${pc(x.t / tot, 1)}</b><small>${pc(noche / (v || 1))} de noche</small></div><div class="cif"><span>${S.por === 'areas' ? 'Carga en su pico' : 'Unidades'}</span><b>${S.por === 'areas' ? (uH[pico] / n).toFixed(1) + ' / hora' : fn(u)}</b><small>${S.por === 'areas' ? `por día, a las ${hh(HORAS[pico])}` : `${(u / n).toFixed(1)} por día`}</small></div></div>
    <div class="bl"><div class="bl-t">Por hora<span>pico ${hh(HORAS[porH.indexOf(Math.max(...porH))])}</span></div>${barras(S.por === 'areas' ? uH.map((q) => q / n) : porH, HORAS.map(hh), S.por === 'areas' ? (q) => q.toFixed(1) + ' u/día' : soles)}</div>
    <div class="bl"><div class="bl-t">Por día de la semana<span>${DIAS_L[porW.indexOf(Math.max(...porW))]}</span></div>${barras(porW, DIAS, soles)}</div>
    ${S.franjas.length ? `<div class="bl"><div class="bl-t">En tus franjas</div><div class="mini">${S.franjas.map((f, i) => `<span>${numFranja(i)}${esc(f.nombre)}</span><span class="b"><i style="width:${(100 * enF[i] / (v || 1)).toFixed(0)}%;background:${FCOL[i]}"></i></span><span class="d">${pc(enF[i] / (v || 1))}</span>`).join('')}</div></div>` : ''}`;
}

// ── Tarjeta 2: la comparación de franjas ─────────────────────────────────
function listaFranjas(cifras) {
  if (S.editando !== null) return formFranja();
  if (!S.franjas.length) return '<div class="fi-de">Todavía no hay franjas.</div><div class="acc"><button type="button" class="btn" id="nueva">+ Nueva franja</button></div>';
  let h = S.franjasAuto ? `<div class="nota">Las ${S.franjas.length} noches que más venden en el rango, de ${sl(S.franjas[0].desde)} a ${sl(S.franjas[0].hasta)}. Cambiá o quitá cualquiera y quedan las tuyas.</div>` : '';
  S.franjas.forEach((f, i) => {
    const c = cifras[i];
    h += `<div class="fcard${S.fsel === f.id ? ' on' : ''}" data-fcard="${f.id}" style="border-left-color:${FCOL[i]}"><div class="t"><b>${numFranja(i)}${esc(f.nombre)}</b><span class="acc"><button type="button" class="btn sec peq" data-editar="${f.id}">Editar</button><button type="button" class="btn sec peq" data-quitar="${f.id}" aria-label="Quitar">✕</button></span></div>
      <div class="d">${esc(describir(f))} · ${c.n} días${cruza(f) ? ' · cruza la medianoche' : ''}</div>${propios(f) ? `<span class="propio">${esc(propios(f))}</span>` : ''}
      <div class="v"><b>${soles(c.a.venta)}</b><span class="fi-de">${soles(c.porDiaV)}/día</span>${pill(c.porDiaV / c.normal - 1, 'vs normal')}${pill(c.porDiaV / c.ap - 1, 'vs año pasado')}</div></div>`;
  });
  if (S.franjas.length < 4) h += '<div class="acc"><button type="button" class="btn" id="nueva">+ Nueva franja</button><span class="fi-de">o prendé «Franjas» en el mapa y arrastrá</span></div>';
  return h;
}
function formFranja() {
  const f = S.editando === 'nueva' ? S.borrador : S.franjas.find((z) => z.id === S.editando);
  const opts = (sel) => { let o = ''; for (let s = 0; s <= 48; s++) o += `<option value="${s}"${s === sel ? ' selected' : ''}>${sl(s)}</option>`; return o; };
  const canalSel = f.canal === null ? '__' : f.canal;
  return `<div class="fform"><div class="fila"><span>Nombre</span><input type="text" id="f-nombre" value="${esc(f.nombre)}" placeholder="p. ej. Cena de viernes"></div>
    <div class="fila"><span>Días</span><div class="seg"><button type="button" data-ftipo="semana" class="${f.tipo === 'semana' ? 'on' : ''}">Días de la semana</button><button type="button" data-ftipo="sueltos" class="${f.tipo === 'sueltos' ? 'on' : ''}">Días sueltos</button></div></div>
    ${f.tipo === 'semana' ? `<div class="chips">${DIAS.map((d, w) => `<button type="button" data-fdia="${w}" class="${f.dias.includes(w) ? 'on' : ''}">${d}</button>`).join('')}</div>`
      : `<div class="chips fechas">${DIAS_R.map((d) => `<button type="button" data-ffecha="${d}" class="${f.fechas.includes(d) ? 'on' : ''}" title="${DIAS_L[dow(d)]}">${DIAS[dow(d)][0]} ${fecha(d)}</button>`).join('')}</div>`}
    <div class="fila"><span>Horario</span><div class="g"><span class="rot">de</span><select class="sel" id="f-desde">${opts(f.desde)}</select><span class="rot">a</span><select class="sel" id="f-hasta">${opts(f.hasta)}</select></div><span class="fi-de">La hora final no entra. Si «a» es antes que «de», cruza la medianoche y cuenta en el día en que empezó.</span></div>
    <div class="fila"><span>Canal de esta franja</span><select class="sel" id="f-canal"><option value="__"${canalSel === '__' ? ' selected' : ''}>Como el resto de la vista</option><option value="todos"${canalSel === 'todos' ? ' selected' : ''}>Todos</option>${D.canales.map((c) => `<option value="${esc(c)}"${canalSel === c ? ' selected' : ''}>${esc(c || 'Sin canal')}</option>`).join('')}</select></div>
    <div class="fila"><span>Ámbito de esta franja</span><select class="sel" id="f-ambito" style="max-width:100%">${opcionesAmbito(f.ambito, true)}</select></div>
    <div class="acc"><button type="button" class="btn" id="f-guardar">Guardar</button><button type="button" class="btn sec" id="f-cancelar">Cancelar</button></div></div>`;
}
function contenidoFranjas(cs) {
  if (!S.franjas.length) return '<div class="vacio2"><b>Comparar horarios</b><span>Prendé «Franjas» en el mapa de arriba y arrastrá (por ejemplo, viernes y sábado de 7 a 11 pm), o creá una franja a mano. Hasta cuatro, cada una contra lo normal y contra el año pasado.</span></div>';
  const col = (i) => `<th>${numFranja(i)}${esc(S.franjas[i].nombre)}</th>`;
  const cabT = `<thead><tr><th></th>${cs.map((_, i) => col(i)).join('')}</tr></thead>`;
  if (S.ctab === 'cifras') {
    const fila = (rot, fnc) => `<tr><td>${rot}</td>${cs.map((c, i) => `<td>${fnc(c, i)}</td>`).join('')}</tr>`;
    const vsTxt = (v) => (isFinite(v) ? `<span class="${v >= 0 ? 'verde' : 'rojo'}">${v >= 0 ? '▲' : '▼'} ${pc(Math.abs(v))}</span>` : '—');
    const dl = (v0, v, i) => (i && v0 && isFinite(v / v0 - 1) ? ` <span class="dl ${v >= v0 ? 'verde' : 'rojo'}">${v >= v0 ? '▲' : '▼'}${pc(Math.abs(v / v0 - 1))}</span>` : '');
    const pd = (c, kk) => c.a[kk] / Math.max(1, c.n);
    let totRango = 0; for (const d of DIAS_R) for (const f of PORDIA.get(d) || []) totRango += f.venta;
    return `<div class="sub-cab"><span class="fi-de">▲▼ al lado de cada cifra: contra la primera franja, por día</span></div><table class="tcomp">${cabT}<tbody>
      ${fila('Cuándo', (c, i) => `<span class="gris">${esc(describir(S.franjas[i]))}</span>`)}
      ${fila('Canal y ámbito', (c, i) => `<span class="gris">${esc(propios(S.franjas[i]) || 'como la vista')}</span>`)}
      ${fila('Venta', (c) => `<b>${soles(c.a.venta)}</b>`)}
      ${fila('Parte del rango', (c) => pc(c.a.venta / (totRango || 1), 1))}
      ${fila('Días', (c) => c.n)}
      ${fila('Venta por día', (c, i) => soles(c.porDiaV) + dl(cs[0].porDiaV, c.porDiaV, i))}
      ${fila('Mesas por día', (c, i) => pd(c, 'mesas').toFixed(1) + dl(pd(cs[0], 'mesas'), pd(c, 'mesas'), i))}
      ${fila('Personas por día', (c, i) => pd(c, 'pax').toFixed(1) + dl(pd(cs[0], 'pax'), pd(c, 'pax'), i))}
      ${fila('Gasto por persona', (c, i) => (c.a.pax ? 'S/ ' + (c.a.ventaCli / c.a.pax).toFixed(0) : '—') + (cs[0].a.pax && c.a.pax ? dl(cs[0].a.ventaCli / cs[0].a.pax, c.a.ventaCli / c.a.pax, i) : ''))}
      ${fila('Unidades por día', (c, i) => fn(pd(c, 'cant')) + dl(pd(cs[0], 'cant'), pd(c, 'cant'), i))}
      ${fila('Descuento', (c) => soles(c.a.desc))}
      ${fila('Contra lo normal', (c) => `${vsTxt(c.porDiaV / c.normal - 1)} <span class="gris">(${isFinite(c.normal) ? soles(c.normal) + '/día' : 'sin datos'})</span>`)}
      ${fila('Contra el año pasado', (c) => `${vsTxt(c.porDiaV / c.ap - 1)} <span class="gris">(${isFinite(c.ap) ? soles(c.ap) + '/día' : 'sin datos'})</span>`)}
      </tbody></table>`;
  }
  if (S.ctab === 'arbol') {
    const idx = S.arbol === 'venta' ? L_VENTA : L_CANT, arbol = new Map();
    cs.forEach((c, i) => { for (const l of c.lin) { const p = PRODS[l[L_PROD]], td = D.tdesc[l[L_TDESC]] || 'Sin descuento'; let node = arbol; [p.grupo, p.sub, p.nombre, td].forEach((kk, lv) => { if (!node.has(kk)) node.set(kk, { v: new Array(cs.length).fill(0), hijos: lv < 3 ? new Map() : null }); const nd = node.get(kk); nd.v[i] += l[idx]; node = nd.hijos; }); } });
    const tot = cs.map((c) => (S.arbol === 'venta' ? c.a.venta : c.a.cant) || 1), mx = Math.max(1, ...[...arbol.values()].flatMap((nn) => nn.v));
    const ord = (m) => [...m.entries()].sort((a, b) => b[1].v.reduce((p, q) => p + q, 0) - a[1].v.reduce((p, q) => p + q, 0));
    const filas = [];
    for (const [g, ng] of ord(arbol)) { filas.push(['ag', g, ng.v, g]); if (!S.abiertos.has(g)) continue;
      for (const [s, ns] of ord(ng.hijos)) { const ks = g + '›' + s; filas.push(['as', s, ns.v, ks]); if (!S.abiertos.has(ks)) continue;
        for (const [p, np] of ord(ns.hijos).slice(0, 20)) { const kp = ks + '›' + p; filas.push(['ap', p, np.v, kp]); if (S.abiertos.has(kp)) for (const [t, nt] of ord(np.hijos)) filas.push(['ad', t, nt.v, '']); } } }
    const fmtA = (q) => (S.arbol === 'venta' ? soles(q) : `${fn(q)} u`);
    return `<div class="sub-cab">${seg('arbol', [['venta', 'Venta'], ['cant', 'Unidades']], S.arbol)}<span class="fi-de">Grupo › Subgrupo › Plato › Tipo de descuento · tocá para abrir · % de su franja</span></div>
      <table class="tcomp">${cabT}<tbody>${filas.map(([t, nom, v, key]) => `<tr class="${t}"${key ? ` data-abrir="${esc(key)}"` : ''}><td>${t !== 'ad' ? (S.abiertos.has(key) ? '▾ ' : '▸ ') : ''}${esc(nom)}</td>${v.map((q, i) => `<td>${q ? `${fmtA(q)} <span class="gris">${pc(q / tot[i])}</span>${t === 'ag' ? `<span class="bar" style="width:${(36 * q / mx).toFixed(0)}px;background:${FCOL[i]}"></span>` : ''}` : '—'}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }
  // Día por día: una fila por fecha, una columna por franja. «·» = la franja no incluye ese día; «—» = no vendió.
  const dias = [...new Set(cs.flatMap((c) => [...c.porDia.keys()]))].sort((a, b) => (a < b ? 1 : -1));
  return `<div class="sub-cab"><span class="fi-de">venta de cada día en cada franja (pedidos) · «—» no vendió · «·» la franja no incluye ese día</span></div>
    <table class="tcomp">${cabT}<tbody>${dias.map((d) => `<tr><td>${DIAS[dow(d)]} ${fecha(d)}${FER.has(d) ? ' *' : ''}</td>${cs.map((c) => { const x = c.porDia.get(d); return x ? `<td>${x.n ? `${soles(x.venta)} <span class="gris">(${x.n})</span>` : '—'}</td>` : '<td class="na">·</td>'; }).join('')}</tr>`).join('')}</tbody></table>`;
}
function tarjeta2() {
  if (!G.R2 || !G.R2.isConnected || !$('ctabs')) return;
  const cifras = S.franjas.map(cifrasFranja);
  $('ctabs').innerHTML = seg('ctab', [['cifras', 'Cifras'], ['arbol', 'Qué se vendió'], ['dias', 'Día por día']], S.ctab, {}, 'modos');
  $('csub').textContent = `por la hora del ${S.base === 'cobro' ? 'cobro' : 'pedido'} · ${filtrosTxt() || 'con eventos, sin venta interna'}`;
  $('flista').innerHTML = listaFranjas(cifras);
  $('fcont').innerHTML = contenidoFranjas(cifras);
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function render() {
  if (!D || !S) return;
  if (S.modo === 'mes' && DIAS_R.length <= 45) S.modo = 'semana';
  if (S.preg === 'que' && delPedido(S.medida)) S.medida = 'venta';
  construir();
  if (S.franjasAuto && G.autoDe !== G.sello) {
    S.franjas = cenasMayores(); G.autoDe = G.sello; S.factiva = null;
    S.nextId = Math.max(S.nextId, S.franjas.length + 1);
  }
  if (G.R1 && G.R1.isConnected && $('kpis')) {
    general(); kpis();
    const lado = S.preg === 'cuando' && comparando() && S.mostrar === 'lado';
    $('cuerpo').classList.toggle('solo', lado);
    $('cuerpo').classList.toggle('ampliado', S.ampliar && S.preg === 'cuando' && !lado);
    let cs = null, items = null;
    if (S.preg === 'cuando') {
      cabeceraCuando();
      if (lado) { ladoALado(); cs = celdas(columnas()); }
      else {
        cs = mapaHoras();
        if (!S.sel || !cs.some((c) => c.id === S.sel.col) || !HORAS.includes(S.sel.h)) {
          const best = cs.flatMap((c) => c.h.map((x) => ({ c, x }))).filter((z) => isFinite(z.x.v)).sort((a, b) => b.x.v - a.x.v)[0];
          S.sel = best ? { col: best.c.id, h: best.x.h } : null; if (best) cs = mapaHoras();
        }
      }
    } else items = graficoQue();
    $('pcuerpo').innerHTML = S.preg === 'cuando' ? (lado ? '' : S.sel ? fichaCelda(cs) : '') : fichaItem(items);
  }
  tarjeta2();
}

// ── Las raíces ───────────────────────────────────────────────────────────
const ESQ1 = `<div class="cab">
    <div class="modos" id="preg"></div><span class="sp"></span><span class="activos" id="activos"></span>
    <button type="button" class="mas" id="mas">Más filtros ▾</button><div id="popw"></div>
  </div>
  <div class="ctrl" id="ctrl"></div>
  <div class="kpis" id="kpis"></div>
  <div class="cuerpo" id="cuerpo">
    <div class="caja grafico"><div class="gcab" id="gcab"></div><div class="svgw" id="svgw"></div><div class="ley" id="ley"></div></div>
    <aside class="caja panel" aria-label="Detalle de lo elegido"><div class="pcuerpo" id="pcuerpo"></div></aside>
  </div>
  <div class="tip" data-zona="tip"></div><div class="toast" role="status" data-zona="toast"></div>`;
const ESQ2 = `<div class="cab cab2"><div class="modos" id="ctabs"></div><span class="sp"></span><span class="fi-de" id="csub"></span></div>
  <div class="cuerpo2">
    <aside class="caja flista" id="flista" aria-label="Franjas"></aside>
    <div class="caja fcont" id="fcont"></div>
  </div>
  <div class="toast" role="status" data-zona="toast"></div>`;

let drag = null;
function celdaEn(ev) {
  const svg = $('svgmapa'); if (!GEO || !svg) return null;
  const r = svg.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
  const j = Math.floor((x - GEO.L) / GEO.cw), i = Math.floor((y - GEO.T) / GEO.filaH);
  if (j < 0 || j >= GEO.n || i < 0 || i >= HORAS.length) return null;
  return { j, i };
}
function irAbajo() {
  // A la tarjeta de las franjas, donde encaja la página (el `scroll-padding`
  // de `.stMain`): `scrollIntoView` la dejaba pegada al borde.
  if (!G.R2) return;
  const host = G.R2.getRootNode && G.R2.getRootNode().host;
  const card = (host && host.closest && host.closest('.st-key-ajuste_graf_card_izq_ventas_franjas')) || G.R2;
  const m = card.closest ? card.closest('.stMain') : null;
  if (!m) { card.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
  const pad = parseFloat(getComputedStyle(m).scrollPaddingTop) || 0;
  m.scrollBy({ top: card.getBoundingClientRect().top - m.getBoundingClientRect().top - pad, behavior: 'smooth' });
}
function mostrarTip(raiz, ev, html) {
  const t = raiz.querySelector('[data-zona="tip"]'); if (!t) return;
  t.innerHTML = html; t.style.display = 'block';
  const r = raiz.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight;
  let left = ev.clientX - r.left + 14, top = ev.clientY - r.top + 14;
  if (left + w > r.width - 4) left = ev.clientX - r.left - w - 14;
  if (ev.clientY + 14 + h > window.innerHeight - 4) top = ev.clientY - r.top - h - 14;
  t.style.left = `${Math.max(0, left)}px`; t.style.top = `${Math.max(0, top)}px`;
}
function ocultarTip(raiz) { const t = raiz.querySelector('[data-zona="tip"]'); if (t) t.style.display = 'none'; }

function alClic(raiz, ev) {
  const t = ev.target, b = t.closest('[data-acc]');
  if (b && !b.disabled) {
    const a = b.dataset.acc, v = b.dataset.v;
    if (a === 'modo') { S.modo = v; S.sel = null; }
    else if (a === 'preg') { S.preg = v; S.ampliar = false; S.menu = false; }
    else if (a === 'por') { S.por = v; S.item = null; }
    else if (a === 'medida') { S.medida = v; if (S.areasAuto) S.areasAuto = 'elegido'; }
    else if (a === 'forma') { S.forma = v; guardar(); }
    else S[a] = v;
    render(); return;
  }
  const pn = t.closest('[data-panel]'); if (pn && !pn.disabled) { const r = pn.dataset.panel; if (S.paneles.has(r)) S.paneles.delete(r); else S.paneles.add(r); guardar(); render(); return; }
  if (t.closest('#mas')) { S.pop = !S.pop; render(); return; }
  if (t.closest('#cerrar-pop')) { S.pop = false; render(); return; }
  if (t.closest('#limpiar')) { Object.assign(S, { canal: 'todos', ambito: '', base: 'pedido', eventos: true, vinterna: false }); render(); return; }
  if (t.closest('#menu')) { S.menu = !S.menu; render(); return; }
  if (t.closest('#ampliar')) { S.ampliar = !S.ampliar; render(); return; }
  if (t.closest('#ir-comp')) { irAbajo(); return; }
  const fa = t.closest('[data-factiva]'); if (fa) { const id = +fa.dataset.factiva; S.factiva = S.factiva === id ? null : id; S.fsel = id; render(); return; }
  const fq = t.closest('[data-fquitar]'); if (fq) { quitarFranja(+fq.dataset.fquitar); return; }
  const bt = t.closest('[data-boton]'); if (bt) { if (bt.dataset.boton === 'todos') S.todos = !S.todos; else S.chicos = !S.chicos; render(); return; }
  const dd = t.closest('[data-dia]'); if (dd) { S.modo = 'dia'; S.sel = { col: dd.dataset.dia, h: S.sel.h }; render(); return; }
  const it = t.closest('[data-item]'); if (it) { S.item = S.item === it.dataset.item && S.por === 'grupos' ? null : it.dataset.item; render(); return; }
  const ir = t.closest('[data-ir]');
  if (ir) {
    S.preg = 'cuando'; S.mostrar = 'mapa';
    if (ir.dataset.ir === 'hora') { const h = +ir.dataset.h, cs = celdas(columnas()), i = HORAS.indexOf(h); const c = cs.reduce((p, z) => (z.h[i].v > p.h[i].v ? z : p)); S.sel = { col: c.id, h }; }
    else { S.modo = 'semana'; const w = +ir.dataset.w, c = celdas(columnas('semana'))[w], best = c.h.reduce((p, z) => (z.v > p.v ? z : p)); S.sel = { col: w, h: best.h }; }
    render(); return;
  }
  if (t.closest('#franja-celda')) {
    const c = celdas(columnas()).find((z) => z.id === S.sel.col);
    const base = S.modo === 'semana' ? { tipo: 'semana', dias: [S.sel.col] } : { tipo: 'sueltos', fechas: c.dias.slice() };
    if (nuevaFranja(Object.assign(base, { desde: S.sel.h * 2, hasta: (S.sel.h * 2 + 2) % 48 || 48 }), raiz)) { S.verFranjas = true; aviso('Franja creada: está abajo, en «Comparación de franjas».', raiz); }
    render(); return;
  }
  if (t.closest('#nueva')) { S.borrador = { id: null, nombre: '', tipo: 'semana', dias: [4, 5], fechas: [], desde: 38, hasta: 46, canal: null, ambito: null }; S.editando = 'nueva'; render(); return; }
  const ed = t.closest('[data-editar]'); if (ed) { ev.stopPropagation(); S.editando = +ed.dataset.editar; render(); return; }
  const qu = t.closest('[data-quitar]'); if (qu) { ev.stopPropagation(); quitarFranja(+qu.dataset.quitar); return; }
  const fcd = t.closest('[data-fcard]'); if (fcd) { S.fsel = +fcd.dataset.fcard; render(); return; }
  const fe = () => (S.editando === 'nueva' ? S.borrador : S.franjas.find((z) => z.id === S.editando));
  const ft = t.closest('[data-ftipo]'); if (ft) { fe().tipo = ft.dataset.ftipo; render(); return; }
  const fd = t.closest('[data-fdia]'); if (fd) { const f = fe(), w = +fd.dataset.fdia; f.dias = f.dias.includes(w) ? f.dias.filter((x) => x !== w) : f.dias.concat(w); render(); return; }
  const ff = t.closest('[data-ffecha]'); if (ff) { const f = fe(), d = ff.dataset.ffecha; f.fechas = f.fechas.includes(d) ? f.fechas.filter((x) => x !== d) : f.fechas.concat(d); render(); return; }
  if (t.closest('#f-cancelar')) { S.editando = null; render(); return; }
  if (t.closest('#f-guardar')) {
    const f = fe();
    f.nombre = $('f-nombre').value.trim(); f.desde = +$('f-desde').value; f.hasta = +$('f-hasta').value;
    const cv = $('f-canal').value; f.canal = cv === '__' ? null : cv;
    const av = $('f-ambito').value; f.ambito = av === '__' ? null : av;
    if ((f.tipo === 'semana' && !f.dias.length) || (f.tipo === 'sueltos' && !f.fechas.length)) { aviso('Elegí al menos un día.', raiz); return; }
    if (f.desde === f.hasta) { aviso('El horario no puede empezar y terminar a la misma hora.', raiz); return; }
    f.nombreAuto = !f.nombre;
    if (!f.nombre) f.nombre = nombreAuto(f);
    if (S.editando === 'nueva' && !nuevaFranja(f, raiz)) return;
    S.editando = null; S.franjasAuto = false; guardar(); render(); return;
  }
  const ab = t.closest('[data-abrir]'); if (ab) { const key = ab.dataset.abrir; if (S.abiertos.has(key)) S.abiertos.delete(key); else S.abiertos.add(key); tarjeta2(); return; }
  if (S.pop && !t.closest('#pop')) { S.pop = false; render(); return; }
  if (S.menu && !t.closest('#minipop')) { S.menu = false; render(); }
}
function quitarFranja(id) {
  S.franjas = S.franjas.filter((f) => f.id !== id);
  if (S.factiva === id) S.factiva = null;
  S.franjasAuto = false; guardar(); render();
}
function alCambiar(ev) {
  const id = ev.target.id;
  if (id === 'verfranjas') { S.verFranjas = ev.target.checked; if (!S.verFranjas) S.factiva = null; }
  else if (id === 'eventos') S.eventos = ev.target.checked;
  else if (id === 'vinterna') S.vinterna = ev.target.checked;
  else if (id === 'cifras') { S.cifras = ev.target.checked; guardar(); }
  else if (id === 'ambito') S.ambito = ev.target.value;
  else if (id === 'otro') S.otro = +ev.target.value;
  else if (id === 'salon') { const v = +ev.target.value; S.salon = v > 0 ? v : null; guardar(); }
  else return;
  render();
}
function enlazar(raiz) {
  // `__vh`: el clic ya lo atendió una tarjeta (el de la ventana no lo vuelve a mirar).
  raiz.addEventListener('click', (ev) => { ev.__vh = true; if (D && S) alClic(raiz, ev); });
  raiz.addEventListener('change', (ev) => { if (D && S) alCambiar(ev); });
  raiz.addEventListener('pointerdown', (ev) => { if (!ev.target.closest('#svgmapa')) return; const c = celdaEn(ev); if (!c) return; drag = { a: c, b: c }; ev.preventDefault(); });
  raiz.addEventListener('pointermove', (ev) => {
    if (drag) {
      const c = celdaEn(ev); if (!c) return; drag.b = c;
      const j0 = Math.min(drag.a.j, c.j), j1 = Math.max(drag.a.j, c.j), i0 = Math.min(drag.a.i, c.i), i1 = Math.max(drag.a.i, c.i), e = $('arrastre');
      if (e && S.verFranjas) { e.setAttribute('x', GEO.L + j0 * GEO.cw); e.setAttribute('y', GEO.T + i0 * GEO.filaH); e.setAttribute('width', (j1 - j0 + 1) * GEO.cw); e.setAttribute('height', (i1 - i0 + 1) * GEO.filaH); }
      return;
    }
    const cel = ev.target.closest('#svgmapa .cel');
    if (!cel || !GEO) { ocultarTip(raiz); return; }
    const c = GEO.cols[+cel.dataset.j], x = c.h[+cel.dataset.i];
    const ref = comparando() ? refCelda(S.comp, c.dias, x.h, divisorDe(c)) : NaN;
    const nom = S.modo === 'dia' ? `${DIAS_L[dow(c.id)]} ${fecha(c.id)}` : S.modo === 'mes' ? MES_L[Number(c.id.slice(5)) - 1] : DIAS_PL[c.id];
    mostrarTip(raiz, ev, `<b>${esc(nom)} · ${hh(x.h)}</b>${MED[S.medida][0]}: ${isFinite(x.v) ? MED[S.medida][1](x.v) : '—'}${isFinite(ref) && ref > 0 ? `<br>${esc(refTexto())}: ${MED[S.medida][1](ref)} (${x.v >= ref ? '+' : '−'}${pc(Math.abs(x.v / ref - 1))})` : ''}`);
  });
  raiz.addEventListener('pointerleave', () => ocultarTip(raiz));
}
function alSoltar() {
  if (!drag || !GEO) { drag = null; return; }
  const { a, b } = drag; drag = null;
  const raiz = G.R1;
  // Sin el interruptor, arrastrar no crea nada: elige la celda donde empezó.
  if ((a.i === b.i && a.j === b.j) || !S.verFranjas) { S.sel = { col: GEO.cols[a.j].id, h: HORAS[a.i] }; render(); return; }
  const j0 = Math.min(a.j, b.j), j1 = Math.max(a.j, b.j), i0 = Math.min(a.i, b.i), i1 = Math.max(a.i, b.i);
  const base = { desde: HORAS[i0] * 2, hasta: (HORAS[i1] * 2 + 2) % 48 || 48 };
  if (S.modo === 'semana') { base.tipo = 'semana'; base.dias = []; base.fechas = []; for (let j = j0; j <= j1; j++) base.dias.push(j); }
  else { base.tipo = 'sueltos'; base.dias = []; base.fechas = GEO.cols.slice(j0, j1 + 1).flatMap((c) => c.dias); }
  const elegida = S.franjas.find((z) => z.id === S.factiva);
  if (elegida) {
    // Redibujar la elegida: otros días y otro horario; el nombre, si era automático, también.
    Object.assign(elegida, base);
    if (elegida.nombreAuto !== false) elegida.nombre = nombreAuto(elegida);
    S.franjasAuto = false; guardar();
    aviso(`«${elegida.nombre}» quedó en ${describir(elegida)}.`, raiz);
  } else {
    const f = nuevaFranja(base, raiz);
    if (f) aviso(`Franja creada: ${f.nombre}. Está abajo, en «Comparación de franjas»; ahí se edita.`, raiz);
  }
  render();
}
function enlazarVentana() {
  if (G.ventana) return;
  G.ventana = true;
  // Lo que pasa afuera de las dos tarjetas: soltar un arrastre, cerrar un
  // desplegable con un clic en otro lado, otro ancho de pantalla.
  window.addEventListener('pointerup', () => { if (G.alSoltar) G.alSoltar(); });
  window.addEventListener('click', (ev) => {
    if (ev.__vh) return;
    if (G.S && (G.S.pop || G.S.menu)) { G.S.pop = false; G.S.menu = false; if (G.render) G.render(); }
  });
  let espera = 0;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => { if (G.render) G.render(); }, 150); });
}
function adoptar2(raiz) {
  G.R2 = raiz;
  if (!raiz.__vhEnlazada) { raiz.__vhEnlazada = true; enlazar(raiz); }
  tarjeta2();
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data) return;
  if (data.parte === 'franjas') {
    let raiz = parentElement.querySelector('.vh2');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'vh vh2';
      raiz.innerHTML = ESQ2;
      parentElement.appendChild(raiz);
    }
    if (G.adoptar2 && G.sello === data.sello) G.adoptar2(raiz);
    else { G.pend2 = raiz; if (!raiz.querySelector('#flista').textContent) raiz.querySelector('#flista').innerHTML = '<div class="fi-de">Cargando…</div>'; }
    return;
  }
  if (!data.P || !data.rango) return;
  let raiz = parentElement.querySelector('.vh1');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'vh vh1';
    raiz.innerHTML = ESQ1;
    parentElement.appendChild(raiz);
    enlazar(raiz);
  }
  G.R1 = raiz;
  G.S = G.S || estadoInicial();
  S = G.S;
  if (G.sello !== data.sello || D !== data) {
    const nuevo = G.sello !== data.sello;
    cargar(data);
    G.sello = data.sello;
    if (nuevo) { S.sel = null; S.item = null; }
  }
  if (data.ir && data.ir.n !== G.irVisto) {
    // El salto desde «Análisis de platos»: el plato, en «Qué se vende a cada hora».
    G.irVisto = data.ir.n;
    Object.assign(S, { preg: 'que', por: 'platos', colsVer: 'hora', item: data.ir.item, ampliar: false });
  }
  G.render = render; G.alSoltar = alSoltar; G.adoptar2 = adoptar2;
  enlazarVentana();
  render();
  if (G.pend2) { const r2 = G.pend2; G.pend2 = null; adoptar2(r2); }
}
