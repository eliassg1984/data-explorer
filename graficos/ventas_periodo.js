// Ventas › «Venta por Periodo» (regla #714).
//
// La monta graficos/ventas_resumen.py con st.components.v2 (sin iframe,
// estilos en un shadow root); `_xlsx.js` va antepuesto (libro, bajar,
// archivo). Es la forma del boceto aprobado con sus cinco mejoras
// (https://claude.ai/artifact/Pb748JiyYM8Wapb49KReMi). Todo se resuelve acá
// —el grano, los filtros, las barras, el tramo, las nueve subvistas, la
// franja, el Detalle, el buscador, el Excel—; a Python vuelve sólo el
// pedido de las líneas de un período viejo (trigger `lineas`), y la fecha,
// que es un botón de Python arriba a la derecha de la tarjeta.
//
// DOS MONTAJES: el grande (`parte: "periodo"`, ventas_resumen.armar_periodo)
// y uno chico (`parte: "lineas"`) con las líneas pedidas, para que el
// mensaje grande no se vuelva a mandar. El estado vive en
// `window.__vtPeriodo`: sobrevive a que Streamlit vuelva a montar la pieza.
//
// Las cuentas son las de ventas_resumen.py y definicion_venta.py: si se
// toca una, se toca la otra (lo vigila test_ventas_periodo.py).

const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DSEM = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const DSEM_MIN = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
const DIA = 864e5;
const GRANOS = ['Día', 'Semana', 'Mes', 'Año'];
const UNIDAD = { Día: ['día', 'días'], Semana: ['semana', 'semanas'], Mes: ['mes', 'meses'], Año: ['año', 'años'] };
const COLORES_CANAL = ['var(--serie-0)', 'var(--serie-1)', 'var(--serie-2)', 'var(--serie-5)', 'var(--serie-6)', 'var(--serie-7)'];
const C = { gris: 'var(--text-secondary)', borde: 'var(--border)', lav: 'var(--border-lavender)', naranja: 'var(--warning)', naranjaT: 'var(--warning-text)',
  verde: 'var(--success)', rojo: 'var(--danger)', texto: 'var(--text-primary)' };
const VENTA = 0, NC = 1, CORTESIA = 2, ANULADO = 3;
const COSTO_ALTO = 0.45, COSTO_ROTO = 0.70, MAX_DIAS = 30, KPI_CANALES = 4, MAX_FORMAS = 6, UMBRAL_IGV = 0.01, RECARGO = 0.13;
const ALTO_TABLA = 34 + 8 * 27, ALTO_FIG = 196, ALTO_FIG_SOLO = 380;
const SUBVISTAS = ['Venta', 'Clientes', 'Canales', 'Propinas', 'Pagos', 'Descuentos', 'Cortesías', 'Costo', 'Cuadre'];
const VER_POR = ['Pedido', 'Mesero', 'Servicio', 'Comprobante'];
const NOMBRE_FORMA = { 'NOTA DE CREDITO': 'Nota de crédito', 'AMERICAN EXPRESS': 'Amex' };

// ── Formato (los de ventas_resumen.py) ───────────────────────────────────
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fin = (v) => v != null && isFinite(v);
const ent = (v) => Math.round(v).toLocaleString('en-US');
const dos = (v) => v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const s0 = (v) => `${v < -0.5 ? '−' : ''}S/ ${ent(Math.abs(v))}`;
const s2 = (v) => `${v < 0 ? '−' : ''}S/ ${dos(Math.abs(v))}`;
function fmtK(v) {
  const m = Math.abs(v), sg = v < 0 ? '-' : '';
  if (m >= 1e6) return `S/ ${sg}${(m / 1e6).toFixed(1)}M`;
  if (m >= 1e3) return `S/ ${sg}${(m / 1e3).toFixed(1)}k`;
  return `S/ ${sg}${m.toFixed(0)}`;
}
const p1 = (x) => `${(x * 100).toFixed(1)}%`;
const p0 = (x) => `${Math.round(x * 100)}%`;
function varVenta(pct) {               // _fmt_var_venta: verde si sube
  const dec = Math.abs(pct) < 10 ? 1 : 0;
  if (+Math.abs(pct).toFixed(dec) === 0) return ['0%', C.gris];
  const t = `${Math.abs(pct).toFixed(dec)}%`;
  return pct > 0 ? ['+' + t, C.verde] : ['−' + t, C.rojo];
}
function txtPp(p, maloSiSube = true, neutro = false) {
  if (p == null) return ['', ''];
  if (Math.abs(p) < 0.05) return ['±0 pp', 'neutro'];
  const malo = maloSiSube ? p > 0 : p < 0;
  return [`${p > 0 ? '+' : '−'}${Math.abs(p).toFixed(1)} pp`, neutro ? 'neutro' : (malo ? 'mal' : 'bien')];
}
function txtVar(v, maloSiSube = false, neutro = false) {
  if (v == null) return ['', ''];
  if (Math.abs(v) < 0.5) return ['0%', 'neutro'];
  const malo = maloSiSube ? v > 0 : v < 0;
  return [`${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(0)}%`, neutro ? 'neutro' : (malo ? 'mal' : 'bien')];
}
const sinTildes = (s) => String(s).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();

// ── Fechas: número de día UTC ────────────────────────────────────────────
const dn = (s) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d) / DIA; };
const ymd = (n) => { const t = new Date(n * DIA); return [t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()]; };
const iso = (n) => { const [y, m, d] = ymd(n); return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
const wd = (n) => (new Date(n * DIA).getUTCDay() + 6) % 7;
const hhmm = (min) => { const m = ((min % 1440) + 1440) % 1440; return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; };
function semanaISO(n) {                 // [año ISO, semana]
  const jue = n - wd(n) + 3, y = ymd(jue)[0];
  const ene4 = Date.UTC(y, 0, 4) / DIA, lun1 = ene4 - wd(ene4);
  return [y, Math.floor((n - wd(n) - lun1) / 7) + 1];
}
function clave(n, gran) {               // _periodo_serie
  const [y, m] = ymd(n);
  if (gran === 'Día') return iso(n);
  if (gran === 'Semana') { const [a, s] = semanaISO(n); return `${a}-S${String(s).padStart(2, '0')}`; }
  if (gran === 'Año') return String(y);
  return `${y}-${String(m).padStart(2, '0')}`;
}
function limites(k, gran) {             // _limites_periodo, en número de día
  if (gran === 'Semana') {
    const [a, s] = k.split('-S').map(Number);
    const ene4 = Date.UTC(a, 0, 4) / DIA, ini = ene4 - wd(ene4) + (s - 1) * 7;
    return [ini, ini + 6];
  }
  if (gran === 'Mes') { const [a, m] = k.split('-').map(Number); return [Date.UTC(a, m - 1, 1) / DIA, Date.UTC(a, m, 0) / DIA]; }
  if (gran === 'Año') return [Date.UTC(+k, 0, 1) / DIA, Date.UTC(+k, 11, 31) / DIA];
  return [dn(k), dn(k)];
}
function variaciones(claves, vals, gran, rango) {
  const parcial = claves.map((k) => { const [a, b] = limites(k, gran); return Math.max(a, rango[0]) > a || Math.min(b, rango[1]) < b; });
  return vals.map((v, i) => {
    const ant = i ? i - 1 : null;
    if (parcial[i]) return ['parcial', null, ant];
    if (ant == null) return ['primera', null, null];
    if (parcial[ant]) return ['ant_parcial', null, ant];
    if (!vals[ant] || vals[ant] <= 0) return ['sin_base', null, ant];
    return ['ok', (v - vals[ant]) / vals[ant] * 100, ant];
  });
}
function rotulo(k, gran, rango) {        // [eje, largo, fila]
  if (gran === 'Día') { const n = dn(k), [y, m, d] = ymd(n); const f = `${DSEM[wd(n)]} ${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}`; return [`${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}`, `${f}/${y}`, f]; }
  if (gran === 'Mes') { const [a, m] = k.split('-').map(Number); const t = `${MES[m - 1]} ${a}`; return [t, t[0].toUpperCase() + t.slice(1), t[0].toUpperCase() + t.slice(1)]; }
  if (gran === 'Año') return [k, k, k];
  const [ini, fin_] = limites(k, gran);
  let a = Math.max(ini, rango[0]), b = Math.min(fin_, rango[1]);
  if (a > b) { a = ini; b = fin_; }
  const dia = (x, mes) => `${DSEM_MIN[wd(x)]} ${ymd(x)[2]}${mes ? ' ' + MES[ymd(x)[1] - 1] : ''}`;
  const eje = a === b ? dia(a, true) : ymd(a)[1] === ymd(b)[1] ? `${dia(a, false)}–${dia(b, true)}` : `${dia(a, true)}–${dia(b, true)}`;
  const largo = `Semana del lun ${ymd(ini)[2]}${ymd(ini)[1] !== ymd(fin_)[1] ? ' ' + MES[ymd(ini)[1] - 1] : ''} al dom ${ymd(fin_)[2]} ${MES[ymd(fin_)[1] - 1]} ${ymd(fin_)[0]}`;
  return [eje, largo, `${eje} ${ymd(fin_)[0]}`];
}
function delAl(a, b) {
  const [ya, ma, da] = ymd(a), [yb, mb, db] = ymd(b);
  if (a === b) return `El ${da} ${MES[ma - 1]} ${ya}`;
  return ya === yb ? `Del ${da} ${MES[ma - 1]} al ${db} ${MES[mb - 1]} ${yb}` : `Del ${da} ${MES[ma - 1]} ${ya} al ${db} ${MES[mb - 1]} ${yb}`;
}
function numeroSunat(num, completo) {   // «B00001000056777» → «B001-56777»
  const m = /^([A-Z])(\d{5})(\d{9})$/.exec(String(num || '').trim());
  if (!m) return String(num || '').trim();
  const corr = parseInt(m[3], 10);
  return `${m[1]}${String(parseInt(m[2], 10)).padStart(3, '0')}-${completo ? String(corr).padStart(8, '0') : corr}`;
}
function tipoCorto(tdoc, clase) {
  const t = tdoc.toLowerCase();
  if (t.startsWith('nc') || clase === NC) return 'Nota de crédito';
  if (t.includes('boleta')) return 'Boleta';
  if (t.includes('factura')) return 'Factura';
  return tdoc ? tdoc[0].toUpperCase() + tdoc.slice(1).toLowerCase() : '';
}
function formaDePago(nombre) { return NOMBRE_FORMA[nombre.toUpperCase()] || nombre || 'Sin forma'; }
function mediana(xs) { const v = xs.filter(fin).sort((a, b) => a - b); if (!v.length) return null; const h = v.length >> 1; return v.length % 2 ? v[h] : (v[h - 1] + v[h]) / 2; }

// ── Los datos (ventas_resumen.armar_periodo) ─────────────────────────────
function preparar(D) {
  const base = dn(D.base);
  const docs = D.docs.map((d, i) => ({ i, num: d[0], tdoc: D.tdocs[d[1]], clase: d[2], porCobrar: d[3], fecha: d[4], emision: d[5],
    ped: d[6], canal: D.canales[d[7]], serv: D.servs[d[8]], mesero: D.meseros[d[9]], pax: d[10], ninos: d[11],
    dia: base + Math.floor(d[4] / 1440) }));
  // Lo de cada comprobante por grupo: de acá salen todas las cuentas menos
  // la tabla de platos.
  const unidades = D.unidades.map((u) => ({ doc: docs[u[0]], grupo: D.grupos[u[1]], venta: u[2], carta: u[3], neto: u[4],
    desc: u[5], costo: u[6], sinCosto: u[7], n: u[8], tdesc: u[9] }));
  const linea = (l) => ({ doc: docs[l[0]], prod: D.prods[l[1]], grupo: D.grupos[l[2]], cant: l[3], venta: l[4] });
  return { D, base, docs, unidades, linea, lineas: D.lineas.map(linea), lineasDesde: base + D.lineas_desde, extra: null,
    sinc: D.sinc.map((x) => ({ doc: docs[x[0]], prod: D.prods[x[1]], grupo: D.grupos[x[2]], venta: x[3] })),
    culp: D.culp.map((x) => ({ doc: docs[x[0]], prod: D.prods[x[1]], grupo: D.grupos[x[2]], pc: x[3], po: x[4], cant: x[5] })),
    igv: D.igv.map(([d, a, b]) => [base + d, a, b]),
    pagos: (D.pagos || []).map((p) => ({ doc: docs[p[0]], monto: p[1], prop: p[2], forma: formaDePago(D.formas[p[3]]) })),
    feriados: new Set(D.feriados.map(dn)), pedidos: D.pedidos, maxDias: D.max_dias || MAX_DIAS,
    alto: { fig: (D.alto || {}).fig || ALTO_FIG, figSolo: (D.alto || {}).fig_solo || ALTO_FIG_SOLO, tabla: (D.alto || {}).tabla || ALTO_TABLA },
    turno: D.turno !== false, franja: D.franja || [],
    opciones: { grupo: D.grupos.filter(Boolean), serv: D.servs.filter(Boolean), canal: D.canales, tdoc: D.tdocs.filter(Boolean) } };
}

// pax_por: un valor por pedido; el de una nota de crédito RESTA (cuenta comprobantes).
function paxPor(filas, porFn, campo = 'pax') {
  const g = new Map();
  filas.forEach((l) => {
    const d = l.doc, k = porFn(l), kk = `${k}\u0001${d.ped}`;
    let e = g.get(kk);
    if (!e) { e = { k, pos: new Set(), neg: new Set(), mp: 0, mn: 0 }; g.set(kk, e); }
    const p = d[campo] || 0;
    if (p > 0) { e.pos.add(d.i); e.mp = Math.max(e.mp, p); } else if (p < 0) { e.neg.add(d.i); e.mn = Math.min(e.mn, p); }
  });
  const out = new Map();
  g.forEach((e) => {
    const dif = e.pos.size - e.neg.size, v = dif > 0 ? e.mp : dif < 0 ? e.mn : 0;
    out.set(e.k, (out.get(e.k) || 0) + v);
  });
  return out;
}
// documentos_por: los comprobantes de una nota RESTAN.
function documentosPor(filas, porFn) {
  const pos = new Map(), neg = new Map();
  filas.forEach((l) => { const m = l.doc.clase === NC ? neg : pos, k = porFn(l); if (!m.has(k)) m.set(k, new Set()); m.get(k).add(l.doc.i); });
  const out = new Map();
  new Set([...pos.keys(), ...neg.keys()]).forEach((k) => out.set(k, (pos.get(k)?.size || 0) - (neg.get(k)?.size || 0)));
  return out;
}
// Los filtros de la vista: Grupo es de cada línea; Servicio, Canal y Documento, del comprobante.
function pasaFiltros(fil, grupo, doc) {
  const ok = (sel, v) => !sel.length || sel.includes(v);
  return ok(fil.grupo, grupo) && ok(fil.serv, doc.serv) && ok(fil.canal, doc.canal) && ok(fil.tdoc, doc.tdoc);
}

// Todo lo de la vista con los filtros y el grano de hoy (`_ventas_resumen`
// de antes, regla #714).
function calcular(B, st) {
  const f = st.fil;
  let todo = B.unidades.filter((u) => pasaFiltros(f, u.grupo, u.doc));
  let tabla = todo.filter((u) => u.doc.clase === VENTA || u.doc.clase === NC);
  if (!tabla.length) return null;
  const gran = st.gran;
  let nota = '';
  if (gran === 'Día') {
    const dias = [...new Set(tabla.map((u) => u.doc.dia))].sort((a, b) => a - b);
    if (dias.length > B.maxDias) {
      const desde = dias[dias.length - B.maxDias];
      todo = todo.filter((u) => u.doc.dia >= desde); tabla = tabla.filter((u) => u.doc.dia >= desde);
      nota = ` Recortado a los últimos ${B.maxDias} días con ventas: para ver más, agrupá por semana o mes.`;
    }
  }
  const K = (u) => clave(u.doc.dia, gran);
  tabla.forEach((u) => { u.k = K(u); });
  const claves = [...new Set(tabla.map((u) => u.k))].sort();
  const okK = new Set(claves);
  const cort = todo.filter((u) => u.doc.clase === CORTESIA && okK.has(u.k = K(u)));
  const anul = todo.filter((u) => u.doc.clase === ANULADO && okK.has(u.k = K(u)));
  const idx = new Map(claves.map((k, i) => [k, i]));
  const n = claves.length;
  const z = () => new Array(n).fill(0);
  const g = { total: z(), carta: z(), neto: z(), desc: z(), costo: z(), docs_v: z(), nc_v: z(), n_docs: z(), n_nc: z(), n_desc: z(),
    anul_s: z(), n_anul: z(), cort_s: z(), n_cort: z(), costo_cort: z(), venta_sin_costo: z(), por_cobrar: z(), propina: z(), n_prop: z(),
    pax: z(), ninos: z(), venta_cli: z(), neto_cli: z() };
  // ¿Qué canales registran clientes? (con_clientes: alguna fila con pax > 0)
  const canCli = new Set(tabla.filter((u) => u.doc.pax > 0).map((u) => u.doc.canal));
  const ncDocs = claves.map(() => new Set());
  tabla.forEach((u) => {
    const i = idx.get(u.k), d = u.doc;
    g.total[i] += u.venta; g.carta[i] += u.carta; g.neto[i] += u.neto; g.desc[i] += u.desc; g.costo[i] += u.costo;
    g.venta_sin_costo[i] += u.sinCosto;
    if (d.clase === VENTA) { g.docs_v[i] += u.venta; if (d.porCobrar) g.por_cobrar[i] += u.venta; } else { g.nc_v[i] += u.venta; ncDocs[i].add(d.i); }
    if (canCli.has(d.canal)) { g.venta_cli[i] += u.venta; g.neto_cli[i] += u.neto; }
  });
  ncDocs.forEach((s, i) => { g.n_nc[i] = s.size; });
  documentosPor(tabla, (u) => u.k).forEach((v, k) => { g.n_docs[idx.get(k)] = v; });
  documentosPor(tabla.filter((u) => u.tdesc), (u) => u.k).forEach((v, k) => { g.n_desc[idx.get(k)] = v; });
  const contar = (us, campoS, campoN, campoC, valFn) => {
    const sets = claves.map(() => new Set());
    us.forEach((u) => { const i = idx.get(u.k); g[campoS][i] += valFn(u); sets[i].add(u.doc.i); if (campoC) g[campoC][i] += u.costo; });
    sets.forEach((s, i) => { g[campoN][i] = s.size; });
  };
  contar(anul, 'anul_s', 'n_anul', null, (u) => u.venta);
  contar(cort, 'cort_s', 'n_cort', 'costo_cort', (u) => u.carta);
  paxPor(tabla, (u) => u.k).forEach((v, k) => { g.pax[idx.get(k)] = v; });
  paxPor(tabla, (u) => u.k, 'ninos').forEach((v, k) => { g.ninos[idx.get(k)] = v; });
  g.ticket = g.venta_cli.map((v, i) => (g.pax[i] ? v / g.pax[i] : null));
  g.ticket_neto = g.neto_cli.map((v, i) => (g.pax[i] ? v / g.pax[i] : null));
  const hayNinos = g.ninos.some((x) => x);
  g.personas = g.pax.map((p, i) => p + g.ninos[i]);
  g.ticket_p = g.venta_cli.map((v, i) => (g.personas[i] ? v / g.personas[i] : null));
  g.ticket_neto_p = g.neto_cli.map((v, i) => (g.personas[i] ? v / g.personas[i] : null));
  g.pcosto = g.costo.map((c, i) => (g.neto[i] ? c / g.neto[i] : null));
  // Propinas (una por pago, sin anulados) y formas de pago (sólo de lo que es venta).
  const docsOk = new Set(todo.map((u) => u.doc.i));
  const propMesero = [];
  const formas = new Map();
  B.pagos.forEach((p) => {
    const d = p.doc;
    if (!d || !docsOk.has(d.i)) return;
    const k = clave(d.dia, gran), i = idx.get(k);
    if (i == null) return;
    if (d.clase !== ANULADO) { g.propina[i] += p.prop; if (p.prop > 0) g.n_prop[i] += 1; propMesero.push({ k, mesero: d.mesero, prop: p.prop }); }
    if (d.clase === VENTA) { if (!formas.has(p.forma)) formas.set(p.forma, z()); formas.get(p.forma)[i] += p.monto; }
  });
  let porForma = [...formas.entries()].sort((a, b) => b[1].reduce((s, x) => s + x, 0) - a[1].reduce((s, x) => s + x, 0));
  let otras = [];
  if (porForma.length > MAX_FORMAS) {
    otras = porForma.slice(MAX_FORMAS - 1).map((x) => x[0]);
    const suma = z(); porForma.slice(MAX_FORMAS - 1).forEach(([, v]) => v.forEach((x, i) => { suma[i] += x; }));
    porForma = porForma.slice(0, MAX_FORMAS - 1).concat([['Otras', suma]]);
  }
  // Los platos sin costo, por período y en el rango; el que dispara el costo; el IGV.
  const sinCosto = new Map(), sinRango = new Map();
  B.sinc.forEach((x) => {
    if (!pasaFiltros(f, x.grupo, x.doc)) return;
    const k = clave(x.doc.dia, gran);
    if (!okK.has(k)) return;
    if (!sinCosto.has(k)) sinCosto.set(k, new Map());
    const m = sinCosto.get(k); m.set(x.prod, (m.get(x.prod) || 0) + x.venta);
    sinRango.set(x.prod, (sinRango.get(x.prod) || 0) + x.venta);
  });
  const ordenar = (m) => [...m.entries()].filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
  const sinCostoProds = new Map([...sinCosto.entries()].map(([k, m]) => [k, ordenar(m)]));
  const culpables = new Map();
  B.culp.forEach((x) => {
    if (!pasaFiltros(f, x.grupo, x.doc)) return;
    const k = clave(x.doc.dia, gran);
    if (!okK.has(k)) return;
    const ex = (x.pc - x.po) * x.cant, c = culpables.get(k);
    if (!c || ex > c.ex) culpables.set(k, { ex, prod: x.prod, pc: x.pc, po: x.po });
  });
  const igv = new Map();
  B.igv.forEach(([d, a, b]) => { const k = clave(d, gran); if (okK.has(k)) igv.set(k, [d, a, b]); });
  // Por canal, en orden de venta.
  const porCanal = new Map();
  tabla.forEach((u) => { if (!porCanal.has(u.doc.canal)) porCanal.set(u.doc.canal, { v: z(), carta: z() }); const e = porCanal.get(u.doc.canal), i = idx.get(u.k); e.v[i] += u.venta; e.carta[i] += u.carta; });
  const canales = [...porCanal.entries()].map(([c, e]) => [c, e.v.reduce((s, x) => s + x, 0)]).filter(([, t]) => t !== 0).sort((a, b) => b[1] - a[1]).map(([c]) => c);
  const fechas = tabla.map((u) => u.doc.dia);
  const rngDatos = [Math.min(...fechas), Math.max(...fechas)];
  const rot = claves.map((k) => rotulo(k, gran, rngDatos));
  return { gran, claves, n, g, tabla, feriados: B.feriados, cort, anul, canales, porCanal, porForma, otras, sinCostoProds, sinRango: ordenar(sinRango),
    culpables, igv, propMesero, hayNinos, nota, rngDatos, eje: rot.map((r) => r[0]), largo: rot.map((r) => r[1]), fila: rot.map((r) => r[2]),
    vars: variaciones(claves, g.total, gran, rngDatos), dias: new Set(tabla.map((u) => u.doc.dia)).size };
}
const marcaIgv = (a, b) => `IGV ${+(a * 100).toFixed(2)}→${+(b * 100).toFixed(2)}%`;
function notaIgv(dia, a, b, pcosto) {
  const rel = (1 + b + RECARGO) / (1 + a + RECARGO) - 1, [y, m, d] = ymd(dia);
  let t = `El ${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y} el IGV pasó de ${+(a * 100).toFixed(2)}% a ${+(b * 100).toFixed(2)}% del neto: con el mismo precio y el mismo costo, `;
  if (pcosto) { const pp = rel * pcosto * 100; t += `un % de costo de ${p1(pcosto)} pasa a ${p1(pcosto * (1 + rel))} (${pp >= 0 ? '+' : '−'}${Math.abs(pp).toFixed(1)} pp)`; }
  else t += `el % de costo ${rel < 0 ? 'baja' : 'sube'} un ${p1(Math.abs(rel))} de sí mismo`;
  return t + ' sin que cambie ningún costo.';
}
const textoSinCosto = (l, n = 2) => (!l || !l.length ? '' : l.slice(0, n).map((x) => x[0]).join(', ') + (l.length > n ? ` y ${l.length - n} más` : ''));
const detalleSinCosto = (l, n = 8) => (!l || !l.length ? '' : l.slice(0, n).map(([p, v]) => `${p} S/ ${ent(v)}`).join(' · ') + (l.length > n ? ` · y ${l.length - n} más` : ''));

window.VentasPeriodo = { preparar, calcular, paxPor, documentosPor, pasaFiltros, clave, limites, variaciones, rotulo, numeroSunat,
  util: { esc, fin, ent, dos, s0, s2, fmtK, p1, p0, varVenta, txtPp, txtVar, sinTildes, iso, ymd, dn, wd, hhmm, delAl, mediana, tipoCorto,
    marcaIgv, notaIgv, textoSinCosto, detalleSinCosto },
  const: { MES, DSEM, GRANOS, UNIDAD, COLORES_CANAL, C, VENTA, NC, CORTESIA, ANULADO, COSTO_ALTO, COSTO_ROTO, KPI_CANALES, ALTO_TABLA,
    ALTO_FIG, ALTO_FIG_SOLO, SUBVISTAS, VER_POR } };

// ── El dibujo: una raíz, todo en el navegador ─────────────────────────────
(function () {
  const V = window.VentasPeriodo, U = V.util, K = V.const, C = K.C;
  const { esc, fin, ent, s0, s2, fmtK, p1, p0, varVenta, txtPp, txtVar } = U;
  const FIL = [['grupo', 'Grupo'], ['serv', 'Servicio'], ['canal', 'Canal'], ['tdoc', 'Documento']];
  const SVG = 'http://www.w3.org/2000/svg';
  void SVG;
  const conAlfa = (c, a) => `color-mix(in srgb, ${c} ${Math.round(a * 100)}%, transparent)`;
  const colores = (n) => Array.from({ length: n }, (_, i) => K.COLORES_CANAL[i % K.COLORES_CANAL.length]);
  const slug = (s) => U.sinTildes(s).replace(/[^0-9a-z]+/g, '_');
  const NUEVO = '';

  function estadoInicial() {
    return { gran: 'Día', fil: { grupo: [], serv: [], canal: [], tdoc: [] }, modo: 'Resumen', sub: 'Venta', ver: 'Pedido', foco: null,
      tramo: null, ped: null, apag: {}, ley: false, menu: null, abierta: null, orden: null, ordenDet: null, como: false, q: '', aviso: '' };
  }

  // ── Lo que se mira: el período en foco (o el tramo, con mejoras) ────────
  function focoClaves(R, st) {
    if (st.tramo) return R.claves.slice(st.tramo[0], st.tramo[1] + 1);
    return st.foco && R.claves.includes(st.foco) ? [st.foco] : null;
  }
  function nombreFoco(R, st) {
    const ks = focoClaves(R, st);
    if (!ks) return '';
    if (ks.length === 1) return R.largo[R.claves.indexOf(ks[0])];
    const a = R.claves.indexOf(ks[0]), b = R.claves.indexOf(ks[ks.length - 1]);
    return `${R.fila[a]} a ${R.fila[b]} (${ks.length} ${K.UNIDAD[R.gran][1]})`;
  }

  // ── Cabecera: título y KPI (`_html_kpi_canales` + `_kpis_extra`) ────────
  function kpis(R, st, M) {
    const g = R.g, sel = M && st.modo === 'Detalle' ? focoClaves(R, st) : null;
    const ix = sel ? sel.map((k) => R.claves.indexOf(k)) : R.claves.map((_, i) => i);
    const s = (a) => ix.reduce((x, i) => x + (a[i] || 0), 0);
    const tot = s(g.total), dias = sel ? new Set(R.tabla.filter((l) => sel.includes(l.k)).map((l) => l.doc.dia)).size : R.dias;
    const t = (rot, val, sub, cls, tip, color) => `<div class="kpi ${cls || ''}" title="${esc(tip || rot)}"${color ? ` style="--kc:${color}"` : ''}>`
      + `<span class="kr">${esc(rot)}</span><span class="kv">${esc(val)}<span class="ks">${esc(sub)}</span></span></div>`;
    const nd = `${ent(dias)} día${dias === 1 ? '' : 's'}`;
    const partes = [t(sel ? `Venta de ${nombreFoco(R, st).replace(/ \(\d+ \S+\)$/, '')}` : 'Venta de la vista', fmtK(tot), nd, 'tot', `Venta: S/ ${U.dos(tot)} · ${nd}`)];
    if (R.canales.length > 1) {
      const cs = R.canales.map((c) => [c, s(R.porCanal.get(c).v)]);
      cs.slice(0, K.KPI_CANALES).forEach(([c, v], i) => partes.push(t(c, fmtK(v), p0(tot ? v / tot : 0), '', `${c}: S/ ${U.dos(v)} · ${p1(tot ? v / tot : 0)}`, colores(cs.length)[i])));
    }
    const pax = s(g.pax), vc = s(g.venta_cli), ni = s(g.ninos);
    if (pax) {
      const tip = [`${ent(pax)} clientes (adultos)${ni ? ` + ${ent(ni)} niños` : ''}`, `ticket S/ ${U.dos(vc / pax)}`, `ticket neto S/ ${U.dos(s(g.neto_cli) / pax)}`];
      if (ni) tip.push(`con niños S/ ${U.dos(vc / (pax + ni))}`);
      if (Math.round((tot - vc) * 100)) tip.push(`sin S/ ${U.dos(tot - vc)} de los canales que no registran clientes`);
      partes.push(t('Clientes', ent(pax), `ticket S/ ${U.dos(vc / pax)}`, '', tip.join(' · ')));
    }
    const pr = s(g.propina);
    if (tot) partes.push(t('Propinas', fmtK(pr), p1(pr / tot), '', `Propinas: S/ ${U.dos(pr)} · ${p1(pr / tot)} de la venta`));
    const d = s(g.desc), ca = s(g.carta);
    if (ca) partes.push(t('Descuentos', fmtK(d), p1(d / ca), '', `Descuentos: S/ ${U.dos(d)} · ${p1(d / ca)} de la carta`));
    partes.push(t('Cortesías', fmtK(s(g.cort_s)), `${ent(s(g.n_cort))} comp.`, '', `Cortesías: S/ ${U.dos(s(g.cort_s))} a precio carta · ${ent(s(g.n_cort))} comprobantes. No suman a la venta`));
    const nc = s(g.nc_v), nnc = s(g.n_nc);
    if (nc) partes.push(t('Notas de crédito', '−' + fmtK(Math.abs(nc)), `${nnc} nota${nnc === 1 ? '' : 's'}`, '', `Notas de crédito: S/ ${U.dos(nc)}. Restan de la venta el día que se emiten, como en el Registro de Ventas`));
    partes.push(t('Anulados', fmtK(s(g.anul_s)), `${ent(s(g.n_anul))} comp.`, '', `Anulados: S/ ${U.dos(s(g.anul_s))} · ${ent(s(g.n_anul))} comprobantes. No suman a la venta`));
    const neto = s(g.neto);
    if (neto) {
      const pc = s(g.costo) / neto, rev = ix.filter((i) => g.pcosto[i] > K.COSTO_ROTO).length;
      partes.push(t('Costo / neto', p1(pc), rev ? `${rev} a revisar` : '', rev || pc > K.COSTO_ALTO ? 'alerta' : '', `Costo de receta ÷ venta neta: ${p1(pc)}${rev ? ` · ${rev} períodos con un costo mayor al precio` : ''}`));
    }
    return partes.join('');
  }

  // La pastilla «Detalle · <período>»: la leyenda, con interruptores.
  function leyenda(R, st) {
    const fx = focoClaves(R, st), i = fx ? R.claves.indexOf(fx[fx.length - 1]) : R.n - 1;
    const filas = [];
    const cols = colores(R.canales.length);
    if (R.canales.length > 1) R.canales.forEach((c, j) => filas.push([cols[j], c, s0(R.porCanal.get(c).v[i]), `canal_${slug(c)}`]));
    else filas.push(['var(--accent)', 'Venta', s0(R.g.total[i]), null]);
    if (R.g.carta.some((x) => x)) filas.push([C.lav, 'Descuento', s0(Math.max(0, R.g.carta[i] - R.g.total[i])), 'desc']);
    filas.push([C.gris, 'Clientes', ent(R.g.pax[i]), 'pax']);
    filas.push([C.naranja, 'Ticket', fin(R.g.ticket[i]) ? `S/ ${U.dos(R.g.ticket[i])}` : '—', 'ticket']);
    return `<button class="ley-b" data-acc="ley">Detalle · ${esc(R.fila[i])} <i>${st.ley ? '▴' : '▾'}</i></button>`
      + (st.ley ? `<div class="ley-p">${filas.map(([c, r, v, k]) => `<label class="ley-f">${k ? `<input type="checkbox" data-acc="apagar" data-v="${k}" ${st.apag[k] ? '' : 'checked'}>` : '<span></span>'}`
        + `<i class="sw" style="background:${c}"></i><span>${esc(r)}</span><b>${esc(v)}</b></label>`).join('')}</div>` : '');
  }

  // ── El gráfico (`_ventas_resumen`, sin Plotly) ──────────────────────────
  function grafico(R, st, ancho, alto, M) {
    const movil = window.matchMedia('(max-width: 900px)').matches;
    const g = R.g, n = R.n, PL = 54, PR = 54, PT = 14, PB = 24, PH = alto - PT - PB, W = Math.max(movil ? 260 : 400, ancho), PW = W - PL - PR, slot = PW / n;
    const vis = R.canales.length > 1 ? R.canales.filter((c) => !st.apag[`canal_${slug(c)}`]) : R.canales;
    const cols = colores(R.canales.length), colDe = (c) => (R.canales.length > 1 ? cols[R.canales.indexOf(c)] : 'var(--accent)');
    const totVis = R.claves.map((_, i) => vis.reduce((s, c) => s + R.porCanal.get(c).v[i], 0));
    const oculto = vis.length < R.canales.length;
    const varsEtq = oculto ? V.variaciones(R.claves, totVis, R.gran, R.rngDatos) : R.vars;
    const hayTapa = g.carta.some((x) => x) && !st.apag.desc;
    const tapa = R.claves.map((_, i) => (hayTapa ? Math.max(0, vis.reduce((s, c) => s + R.porCanal.get(c).carta[i] - R.porCanal.get(c).v[i], 0)) : 0));
    const alturaBarra = totVis.map((t, i) => t + tapa[i]);
    const hi = Math.max(1, ...alturaBarra);
    const rotar = !movil && n > 12;
    const cadaEtiqueta = movil ? Math.max(1, Math.ceil(n / Math.max(1, Math.floor(PW / 64)))) : 1;
    const largoEtq = Math.max(...totVis.map((t, i) => (U.fmtK(t) + ' ' + (varsEtq[i][0] === 'ok' ? '+12.3%' : 'parcial')).length));
    const etq = rotar ? Math.min(largoEtq * 5.4 * 0.8, PH * 0.45) : 30;
    const yMax = hi * PH / (PH - etq);
    const Y = (v) => PT + PH - v / yMax * PH, X = (i) => PL + (i + 0.5) * slot;
    const fx = M || st.modo === 'Detalle' ? focoClaves(R, st) : null;
    const enFoco = (i) => !fx || st.modo !== 'Detalle' || fx.includes(R.claves[i]);
    let s = `<svg width="${W}" height="${alto}" viewBox="0 0 ${W} ${alto}" role="img" aria-label="Venta por período, partida por canal">`;
    // Fin de semana y feriados (en Día), y los lunes punteados.
    if (R.gran === 'Día') {
      R.claves.forEach((k, i) => {
        const d = U.dn(k), fer = R.feriados.has(d);
        if (fer || U.wd(d) >= 5) s += `<rect x="${PL + i * slot}" y="${PT}" width="${slot}" height="${PH}" style="fill:${fer ? C.naranjaT : C.gris}" fill-opacity="${fer ? 0.10 : 0.07}"/>`;
        if (fer) s += `<text class="fer" x="${X(i)}" y="${PT - 3}" text-anchor="middle">feriado</text>`;
        if (i && U.wd(d) === 0) s += `<line x1="${PL + i * slot}" x2="${PL + i * slot}" y1="${PT}" y2="${PT + PH}" style="stroke:${C.borde}" stroke-dasharray="2 3"/>`;
      });
    } else {
      R.claves.forEach((k, i) => {
        const [a, b] = V.limites(k, R.gran); let nf = 0;
        R.feriados.forEach((f) => { if (f >= a && f <= b) nf += 1; });
        if (nf) s += `<text class="fer" x="${X(i)}" y="${PT - 3}" text-anchor="middle">${nf} feriado${nf === 1 ? '' : 's'}</text>`;
      });
    }
    // Eje de la venta.
    const paso = (r) => { const b = Math.pow(10, Math.floor(Math.log10(r || 1))), f = r / b; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * b; };
    const py = paso(yMax / 4);
    for (let v = 0; v <= yMax; v += py) s += `<line x1="${PL}" x2="${W - PR}" y1="${Y(v)}" y2="${Y(v)}" style="stroke:${C.borde}"/><text class="ty" x="${PL - 6}" y="${Y(v) + 3.5}" text-anchor="end">S/ ${v >= 1000 ? +(v / 1000).toFixed(1) + 'k' : v}</text>`;
    // Las barras: un tramo por canal y la tapa del descuento.
    const bw = slot * 0.7;
    R.claves.forEach((k, i) => {
      let y0 = 0;
      vis.forEach((c) => {
        const v = R.porCanal.get(c).v[i];
        if (v > 0) s += `<rect x="${X(i) - bw / 2}" y="${Y(y0 + v)}" width="${bw}" height="${Y(y0) - Y(y0 + v)}" style="fill:${enFoco(i) ? colDe(c) : conAlfa(colDe(c), 0.2)}"/>`;
        y0 += v;
      });
      if (tapa[i] > 0) s += `<rect x="${X(i) - bw / 2}" y="${Y(y0 + tapa[i])}" width="${bw}" height="${Y(y0) - Y(y0 + tapa[i])}" style="fill:${enFoco(i) ? C.lav : conAlfa(C.lav, 0.2)}"/>`;
      // La etiqueta: total y variación (o «parcial»).
      const [est, pct] = varsEtq[i];
      const [vt, vc] = est === 'ok' ? varVenta(pct) : est === 'parcial' ? ['parcial', C.gris] : ['', C.gris];
      if (totVis[i] && i % cadaEtiqueta === 0) {
        const yTop = Y(alturaBarra[i]) - 4;
        if (rotar) s += `<text class="et" transform="translate(${X(i) + 3},${yTop}) rotate(-90)">${esc(fmtK(totVis[i]))}<tspan dx="4" style="fill:${vc}" font-weight="700"${est === 'parcial' ? ' font-style="italic"' : ''}>${esc(vt)}</tspan></text>`;
        else s += `<text class="et" x="${X(i)}" y="${yTop - (!movil && vt ? 12 : 0)}" text-anchor="middle">${esc(fmtK(totVis[i]))}</text>${!movil && vt ? `<text class="et" x="${X(i)}" y="${yTop}" text-anchor="middle" style="fill:${vc}" font-weight="700">${esc(vt)}</text>` : ''}`;
      }
    });
    // Clientes, punteado sobre su eje a la derecha.
    if (!st.apag.pax && g.pax.some((x) => x)) {
      const pm = Math.max(...g.pax) * 1.15 || 1, Y2 = (v) => PT + PH - v / pm * PH;
      s += `<polyline points="${g.pax.map((v, i) => `${X(i)},${Y2(v)}`).join(' ')}" fill="none" style="stroke:${C.gris}" stroke-width="1.5" stroke-dasharray="3 3"/>`;
      const p2 = paso(pm / 3);
      for (let v = 0; v <= pm; v += p2) s += `<text class="ty" x="${W - PR + 8}" y="${Y2(v) + 3.5}">${ent(v)}</text>`;
      s += `<text class="tt" transform="translate(${W - 8},${PT + PH / 2}) rotate(-90)" text-anchor="middle">Clientes</text>`;
    }
    // El ticket, en su propia escala y sin eje: su último valor escrito.
    if (!st.apag.ticket && g.ticket.some(fin)) {
      const ts = g.ticket.filter(fin), lo = Math.min(...ts), hi2 = Math.max(...ts), pad = (hi2 - lo) * 0.15 || hi2 * 0.1;
      const Y3 = (v) => PT + PH - (v - (lo - pad)) / ((hi2 + pad) - (lo - pad)) * PH;
      const pts = g.ticket.map((v, i) => (fin(v) ? `${X(i)},${Y3(v)}` : null)).filter(Boolean).join(' ');
      s += `<polyline points="${pts}" fill="none" style="stroke:${C.naranja}" stroke-width="2"/>`;
      g.ticket.forEach((v, i) => { if (fin(v)) s += `<circle cx="${X(i)}" cy="${Y3(v)}" r="2.6" style="fill:${C.naranja}"/>`; });
      const u = g.ticket[n - 1];
      if (fin(u)) s += `<text class="tk" x="${X(n - 1)}" y="${Y3(u) - 7}" text-anchor="end">Ticket S/ ${ent(u)}</text>`;
    }
    // Rótulos del eje: los que entran horizontales.
    const caben = Math.max(1, Math.floor(PW / (Math.max(...R.eje.map((e) => e.length)) * 6.3 + 12))), pasoX = Math.max(1, Math.ceil(n / caben));
    R.eje.forEach((e, i) => { if (i % pasoX === 0) s += `<text class="tx" x="${X(i)}" y="${alto - 6}" text-anchor="middle">${esc(e)}</text>`; });
    // La zona de cada período, a toda la altura: el cursor, el clic y (mejoras) el arrastre.
    R.claves.forEach((k, i) => { s += `<rect class="hit${st.tramo && i >= st.tramo[0] && i <= st.tramo[1] ? ' tr' : ''}" data-acc="barra" data-i="${i}" x="${PL + i * slot}" y="${PT}" width="${slot}" height="${PH}"/>`; });
    s += '</svg>';
    return { svg: s, X, W };
  }
  function ficha(R, st, i) {
    const g = R.g, k = R.claves[i], [est, pct, ant] = R.vars[i];
    const rotTot = { Día: 'Total del día', Semana: 'Total de la semana', Mes: 'Total del mes', Año: 'Total del año' }[R.gran];
    let v = '';
    if (est === 'ok') { const [t, c] = varVenta(pct); v = `vs ${esc(R.largo[ant])}: <b style="color:${c}">${t}</b>`; }
    else if (est === 'parcial') v = '<i>Período incompleto en el rango: sin variación</i>';
    else if (est === 'ant_parcial') v = `<i>Sin variación: la barra anterior (${esc(R.largo[ant])}) está incompleta en el rango</i>`;
    else if (est === 'sin_base') v = `<i>Sin variación: ${esc(R.largo[ant])} no vendió</i>`;
    else v = '<i>Primera barra: sin anterior para comparar</i>';
    let h = `<b>${esc(R.largo[i])}</b><div>${rotTot}: S/ ${ent(g.total[i])}</div><div>${v}</div>`;
    if (R.canales.length > 1) h += '<div class="tg">Por canal</div>' + R.canales.map((c) => { const x = R.porCanal.get(c).v[i]; return x ? `<div>${esc(c)}: S/ ${ent(x)} · ${p0(g.total[i] ? x / g.total[i] : 0)}</div>` : ''; }).join('');
    if (g.carta[i]) h += `<div><b>Descuentos</b>: S/ ${ent(Math.max(0, g.carta[i] - g.total[i]))} · ${p1((g.carta[i] - g.total[i]) / g.carta[i])} de la carta</div>`;
    h += `<div>Clientes: ${ent(g.pax[i])}${fin(g.ticket[i]) ? ` · Ticket S/ ${U.dos(g.ticket[i])} · neto S/ ${U.dos(g.ticket_neto[i])}` : ''}</div>`;
    void k;
    return h;
  }

  // ── El Resumen: una fila por período (`_zona_resumen`) ─────────────────
  function subvistas(R) {
    const g = R.g, hay = (a) => a.some((x) => x), S = 104, out = {};
    const venta = [['carta', 'Carta', 'soles0', S, 'Venta a precio de CARTA: lo que se habría cobrado sin descuentos'],
      ['valor', 'Venta', 'celda', 118, 'Venta documentada, con IGV y recargo. Sin cortesías ni anulados'],
      ['neto', 'Neto', 'soles0', S, 'Venta sin IGV ni recargo: la base del % de costo'],
      ['costo', 'Costo histórico', 'soles0', 132, 'Costo histórico de lo vendido, incluidos combos y propiedades'],
      ['pcosto', '% costo', 'celda', 176, 'Costo ÷ Neto, y su cambio en pp contra la barra anterior'],
      ['pax', 'Pax', 'entero', 72, 'Clientes del período'],
      ['ticket', 'Ticket', 'celda', 132, 'Venta ÷ clientes, sin la venta de los canales que no registran clientes (Rappi). Y su variación'],
      ['ticket_neto', 'Ticket neto', 'celda', 132, 'Neto (sin IGV ni recargo) ÷ clientes: el «Ticket Pro.» de la Liquidación de Cajero del POS'],
      ['variacion', 'Var. venta', 'var', S, 'Variación de la venta contra la barra anterior']];
    out.Venta = [venta, 'Precios, % de costo, clientes, ticket y variación.'];
    const cli = [['valor', 'Venta', 'celda', 118, 'Venta documentada: pagados y por cobrar, menos notas de crédito'],
      ['sin_cli', 'Fuera del ticket', 'celda', 128, 'Venta de los canales que no registran clientes (Rappi): no entra en ningún ticket'],
      ['pax', 'Adultos', 'entero', 84, 'Clientes: los adultos, como cuenta el POS']];
    if (R.hayNinos) cli.push(['ninos', 'Niños', 'entero', 72, 'Niños de las mesas'], ['personas', 'Personas', 'entero', 92, 'Adultos + niños']);
    cli.push(['ticket', 'Ticket', 'celda', 132, 'Venta ÷ adultos, y su variación']);
    if (R.hayNinos) cli.push(['ticket_p', 'Ticket c/ niños', 'celda', 140, 'Venta ÷ personas (adultos + niños)']);
    cli.push(['ticket_neto', 'Ticket neto', 'celda', 132, 'Neto (sin IGV ni recargo) ÷ adultos: el «Ticket Pro.» de la Liquidación de Cajero del POS']);
    if (R.hayNinos) cli.push(['ticket_neto_p', 'Neto c/ niños', 'celda', 132, 'Neto ÷ personas (adultos + niños)']);
    out.Clientes = [cli, R.hayNinos ? 'Ticket por adulto y con niños, con impuestos y neto.' : 'Ticket por adulto. Los niños no vienen todavía en la consulta de ventas.'];
    if (R.canales.length > 1) {
      const c = [['valor', 'Venta', 'celda', 118, 'Venta documentada: pagados y por cobrar, menos notas de crédito']];
      R.canales.forEach((cn, k) => c.push([`c${k}_v`, cn, 'celda', 128, `Venta de ${cn} y su variación contra la barra anterior`], [`c${k}_p`, `% ${cn}`, 'celda', 118, `Qué parte de la venta fue de ${cn}, y su cambio en pp`]));
      out.Canales = [c, 'Venta y peso de cada canal.'];
    }
    if (hay(g.propina)) out.Propinas = [[['valor', 'Venta', 'celda', 118, 'Venta documentada: pagados y por cobrar, menos notas de crédito'],
      ['propina', 'Propina', 'celda', 118, 'Propinas del período (una por pago) y su variación'], ['pprop', '% de la venta', 'celda', 132, 'Propina ÷ venta, y su cambio en pp'],
      ['prop_cli', 'Por cliente', 'soles', 104, 'Propina ÷ clientes'], ['n_prop', 'Pagos c/propina', 'entero', 124, 'Pagos que dejaron propina'],
      ['pax', 'Pax', 'entero', 72, 'Clientes del período']], 'Una propina por pago.'];
    if (R.porForma.length) {
      const c = [['valor', 'Venta', 'celda', 118, 'Venta documentada: pagados y por cobrar, menos notas de crédito']];
      R.porForma.forEach(([fm], k) => c.push([`f${k}_v`, fm, 'celda', 112, `Pagado con ${fm === 'Otras' && R.otras.length ? R.otras.join(', ') : fm} y su parte de los pagos de comprobantes del período`]));
      c.push(['cobrado', 'Pagos registrados', 'celda', 150, 'Pagos de los comprobantes seleccionados, agrupados por la fecha del comprobante'],
        ['por_cobrar', 'Por cobrar', 'celda', 112, 'Importe de comprobantes en estado por cobrar, según la última actualización']);
      out.Pagos = [c, 'Pagos asociados a los comprobantes del período; un pago una vez y por cobrar aparte.'];
    }
    if (hay(g.carta)) out.Descuentos = [[['carta', 'Carta', 'soles0', S, 'Venta a precio de carta'], ['valor', 'Venta', 'celda', 118, 'Venta documentada: pagados y por cobrar, menos notas de crédito'],
      ['desc', 'Descuento', 'celda', 118, 'Carta − Venta, y su variación'], ['pdesc', '% desc.', 'celda', 132, 'Descuento ÷ carta, y su cambio en pp'],
      ['n_desc', 'Comprob. c/desc.', 'celda', 128, 'Comprobantes con algún descuento, de todos los del período'], ['ptrx', '% comprob.', 'celda', 112, 'Qué parte de los comprobantes tuvo descuento']],
    'Carta − Venta, y en cuántos comprobantes.'];
    out['Cortesías'] = [[['carta', 'Carta vendida', 'soles0', 112, 'Venta a precio de carta (sin cortesías)'], ['cort', 'Cortesías', 'celda', 118, 'Cortesías a precio carta, y su variación'],
      ['pcort', '% cortesía', 'celda', 132, 'Cortesías ÷ carta vendida, y su cambio en pp'], ['n_cort', 'Comprob.', 'entero', 92, 'Comprobantes tipo CORTESIA'],
      ['costo_cort', 'Costaron', 'soles0', S, 'Costo de receta de las cortesías']], 'A precio carta; no suman a la venta.'];
    out.Costo = [[['neto', 'Neto', 'soles0', S, 'Venta sin IGV ni recargo'], ['costo_v', 'Costo histórico', 'celda', 142, 'Costo histórico de lo vendido, incluidos combos y propiedades, y su variación'],
      ['pcosto', '% costo', 'celda', 176, 'Costo ÷ Neto, y su cambio en pp. «revisar»: un plato con costo mayor a su precio infla el período'],
      ['sin_costo', 'Sin costo', 'soles0', S, 'Venta de platos SIN costo cargado: baja el % de costo'], ['psin', '% venta sin costo', 'celda', 132, 'Qué parte de la venta no tiene costo cargado'],
      ['sin_que', 'Qué se vendió sin costo', 'texto', 220, 'Lo vendido sin costo cargado, de mayor a menor venta: lo que hay que corregir en el POS. Con el cursor, los montos'],
      ['revisar', 'A revisar', 'texto', 180, 'El plato con mayor exceso de costo sobre su precio, en los períodos marcados «revisar»']], 'Costo sobre neto; «sin costo» baja el %.'];
    out.Cuadre = [[['docs_v', 'Facturas y boletas', 'celda', 150, 'Facturas y boletas pagadas o por cobrar: lo mismo que registra el sistema de caja'],
      ['nc_v', 'Notas de crédito', 'celda', 140, 'Notas de crédito emitidas en el período. Restan de la venta el día que se emiten, como en el Registro de Ventas'],
      ['valor', '= Venta', 'celda', 118, 'Facturas y boletas − notas de crédito'], ['cort_c', 'Cortesías', 'celda', 132, 'Aparte: a precio carta. No son venta'],
      ['anul', 'Anulados', 'celda', 132, 'Aparte: comprobantes anulados. No son venta']], 'Venta = facturas y boletas − notas de crédito; cortesías y anulados, aparte.'];
    return out;
  }
  // Una fila por período, con su texto, su nota, su barrita y su bandera.
  function filasResumen(R) {
    const g = R.g, n = R.n, tot = g.total, mx = (a) => Math.max(0, ...a.filter(fin));
    const rat = (a, b) => a.map((x, i) => (b[i] ? x / b[i] : null));
    const pdesc = rat(g.desc, g.carta), pcort = rat(g.cort_s, g.carta), pprop = rat(g.propina, tot), psin = rat(g.venta_sin_costo, tot), ptrx = rat(g.n_desc, g.n_docs);
    const pp = (a, i) => (!i || a[i] == null || a[i - 1] == null ? null : (a[i] - a[i - 1]) * 100);
    const vr = (a, i) => { const v = R.vars[i]; return v[0] !== 'ok' || a[i] == null || !a[v[2]] ? null : (a[i] - a[v[2]]) / a[v[2]] * 100; };
    const cobrado = R.claves.map((_, i) => R.porForma.reduce((s, [, v]) => s + v[i], 0));
    const share = R.canales.map((c) => R.porCanal.get(c).v.map((x, i) => (tot[i] ? x / tot[i] : 0)));
    const out = [];
    for (let i = 0; i < n; i += 1) {
      const k = R.claves[i], r = { __k: k, __i: i, periodo: { t: R.fila[i], v: R.claves[i] } };
      const cel = (campo, v, t, nota = ['', ''], extra = {}) => { r[campo] = { v, t, nota, ...extra }; };
      const bar = (w, tono = '') => ({ w, tono });
      if (R.gran === 'Día' && R.feriados.has(U.dn(k))) r.periodo.nota = ['feriado', 'alto'];
      const ig = R.igv.get(k);
      if (ig) { const m = U.marcaIgv(ig[1], ig[2]); r.periodo.nota = [r.periodo.nota ? `${r.periodo.nota[0]} · ${m}` : m, 'alto']; r.periodo.tip = `${R.fila[i]} · ${U.notaIgv(ig[0], ig[1], ig[2], i && g.pcosto[i - 1] != null ? g.pcosto[i - 1] : g.pcosto[i])}`; }
      cel('carta', g.carta[i], s0(g.carta[i])); cel('neto', g.neto[i], s0(g.neto[i])); cel('costo', g.costo[i], s0(g.costo[i]));
      cel('valor', tot[i], s0(tot[i]), undefined, { bar: bar(tot[i] / mx(tot)) });
      const pc = g.pcosto[i];
      if (pc != null) {
        cel('pcosto', pc, p1(pc), txtPp(pp(g.pcosto, i)), { cls: pc > K.COSTO_ROTO ? 'roto' : pc > K.COSTO_ALTO ? 'alto' : '', bar: bar(Math.min(pc, 1), pc > K.COSTO_ROTO ? 'roja' : pc > K.COSTO_ALTO ? 'ambar' : ''), band: pc > K.COSTO_ROTO ? 'revisar' : '' });
        cel('costo_v', g.costo[i], s0(g.costo[i]), txtVar(vr(g.costo, i), false, true));
        const cu = R.culpables.get(k); cel('revisar', 0, cu && pc > K.COSTO_ROTO ? cu.prod : '');
      }
      cel('sin_costo', g.venta_sin_costo[i], s0(g.venta_sin_costo[i]));
      cel('psin', psin[i], p0(psin[i] || 0), undefined, { bar: bar((psin[i] || 0) / (mx(psin) || 1), psin[i] > 0.3 ? 'ambar' : '') });
      const sp = R.sinCostoProds.get(k) || [];
      cel('sin_que', 0, U.textoSinCosto(sp), undefined, { tip: U.detalleSinCosto(sp) });
      cel('pax', g.pax[i], ent(g.pax[i]));
      ['ticket', 'ticket_neto', 'ticket_p', 'ticket_neto_p'].forEach((t) => { const x = g[t][i]; cel(t, x, fin(x) ? `S/ ${U.dos(x)}` : '—', txtVar(vr(g[t], i))); });
      cel('ninos', g.ninos[i], ent(g.ninos[i])); cel('personas', g.personas[i], ent(g.personas[i]));
      const fuera = Math.round((tot[i] - g.venta_cli[i]) * 100) / 100; cel('sin_cli', fuera, fuera ? s0(fuera) : '—');
      R.canales.forEach((c, kk) => {
        const m = R.porCanal.get(c).v; cel(`c${kk}_v`, m[i], s0(m[i]), txtVar(vr(m, i)));
        cel(`c${kk}_p`, share[kk][i], p1(share[kk][i]), txtPp(pp(share[kk], i), true, true), { bar: bar(share[kk][i] / (mx(share[kk]) || 1), kk ? 'cian' : '') });
      });
      cel('propina', g.propina[i], s0(g.propina[i]), txtVar(vr(g.propina, i)));
      cel('pprop', pprop[i], p1(pprop[i] || 0), txtPp(pp(pprop, i), false), { bar: bar((pprop[i] || 0) / (mx(pprop) || 1)) });
      cel('n_prop', g.n_prop[i], ent(g.n_prop[i])); cel('prop_cli', g.pax[i] ? g.propina[i] / g.pax[i] : null, g.pax[i] ? `S/ ${U.dos(g.propina[i] / g.pax[i])}` : '—');
      R.porForma.forEach(([, v], kk) => { const m = v[i], p = cobrado[i] ? m / cobrado[i] : 0; cel(`f${kk}_v`, m, m ? s0(m) : '—', m ? [p0(p), 'neutro'] : ['', '']); });
      cel('por_cobrar', g.por_cobrar[i], g.por_cobrar[i] ? s0(g.por_cobrar[i]) : '—'); cel('cobrado', cobrado[i], s0(cobrado[i]));
      cel('desc', g.desc[i], s0(g.desc[i]), txtVar(vr(g.desc, i), true)); cel('pdesc', pdesc[i], p1(pdesc[i] || 0), txtPp(pp(pdesc, i)), { bar: bar((pdesc[i] || 0) / (mx(pdesc) || 1)) });
      cel('n_desc', g.n_desc[i], `${ent(g.n_desc[i])} / ${ent(g.n_docs[i])}`); cel('ptrx', ptrx[i], p0(ptrx[i] || 0), txtPp(pp(ptrx, i)));
      cel('cort', g.cort_s[i], s0(g.cort_s[i]), txtVar(vr(g.cort_s, i), true)); cel('pcort', pcort[i], p1(pcort[i] || 0), txtPp(pp(pcort, i)), { bar: bar((pcort[i] || 0) / (mx(pcort) || 1)) });
      cel('n_cort', g.n_cort[i], ent(g.n_cort[i])); cel('costo_cort', g.costo_cort[i], s0(g.costo_cort[i]));
      [['docs_v', g.docs_v, null], ['nc_v', g.nc_v, g.n_nc], ['cort_c', g.cort_s, g.n_cort], ['anul', g.anul_s, g.n_anul]].forEach(([c, a, nn]) => {
        const x = Math.round(a[i] * 100) / 100, cu = nn ? nn[i] : 0; cel(c, x, x ? s0(x) : '—', cu ? [`${cu} comp.`, 'neutro'] : ['', '']);
      });
      const v = R.vars[i];
      r.variacion = { v: v[0] === 'ok' ? v[1] : null, t: v[0] === 'ok' ? varVenta(v[1])[0] : v[0] === 'parcial' ? 'parcial' : '—', color: v[0] === 'ok' ? varVenta(v[1])[1] : C.gris };
      out.push(r);
    }
    return out;
  }
  function totalResumen(R) {
    const g = R.g, s = (a) => a.reduce((x, y) => x + (y || 0), 0), tv = s(g.total), t = {};
    t.periodo = `Total · ${ent(R.n)} ${K.UNIDAD[R.gran][R.n === 1 ? 0 : 1]}`;
    t.valor = s0(tv); t.carta = s0(s(g.carta)); t.neto = s0(s(g.neto)); t.costo = s0(s(g.costo)); t.costo_v = t.costo;
    t.pcosto = s(g.neto) ? p1(s(g.costo) / s(g.neto)) : ''; t.sin_costo = s0(s(g.venta_sin_costo)); t.psin = tv ? p0(s(g.venta_sin_costo) / tv) : '';
    t.sin_que = U.textoSinCosto(R.sinRango, 3);
    const px = s(g.pax), vc = s(g.venta_cli), pe = s(g.personas);
    t.pax = ent(px); t.ticket = px ? `S/ ${U.dos(vc / px)}` : '—'; t.ticket_neto = px ? `S/ ${U.dos(s(g.neto_cli) / px)}` : '—';
    t.ticket_p = pe ? `S/ ${U.dos(vc / pe)}` : '—'; t.ticket_neto_p = pe ? `S/ ${U.dos(s(g.neto_cli) / pe)}` : '—'; t.ninos = ent(s(g.ninos)); t.personas = ent(pe);
    t.sin_cli = Math.round((tv - vc) * 100) ? s0(tv - vc) : '—';
    R.canales.forEach((c, k) => { const m = s(R.porCanal.get(c).v); t[`c${k}_v`] = s0(m); t[`c${k}_p`] = tv ? p1(m / tv) : ''; });
    t.propina = s0(s(g.propina)); t.pprop = tv ? p1(s(g.propina) / tv) : ''; t.n_prop = ent(s(g.n_prop)); t.prop_cli = px ? `S/ ${U.dos(s(g.propina) / px)}` : '';
    const cob = R.porForma.reduce((x, [, v]) => x + s(v), 0);
    R.porForma.forEach(([, v], k) => { t[`f${k}_v`] = s0(s(v)); }); t.cobrado = s0(cob); t.por_cobrar = s(g.por_cobrar) ? s0(s(g.por_cobrar)) : '—';
    t.desc = s0(s(g.desc)); t.pdesc = s(g.carta) ? p1(s(g.desc) / s(g.carta)) : ''; t.n_desc = `${ent(s(g.n_desc))} / ${ent(s(g.n_docs))}`; t.ptrx = s(g.n_docs) ? p0(s(g.n_desc) / s(g.n_docs)) : '';
    [['docs_v', g.docs_v], ['nc_v', g.nc_v], ['cort_c', g.cort_s], ['anul', g.anul_s]].forEach(([c, a]) => { const x = s(a); t[c] = x ? s0(x) : '—'; });
    t.cort = s0(s(g.cort_s)); t.pcort = s(g.carta) ? p1(s(g.cort_s) / s(g.carta)) : ''; t.n_cort = ent(s(g.n_cort)); t.costo_cort = s0(s(g.costo_cort));
    t.variacion = '';
    return t;
  }
  // La franja que se despliega debajo de un período (`_franja`).
  function franja(R, i) {
    const g = R.g, tot = g.total, k = R.claves[i], partes = [];
    const span = ([t, c]) => (t ? `<span class="n ${c}">${esc(t)}</span>` : '');
    const vr = (a) => { const v = R.vars[i]; return v[0] !== 'ok' || !a[v[2]] ? null : (a[i] - a[v[2]]) / a[v[2]] * 100; };
    const pp = (a) => (!i || a[i] == null || a[i - 1] == null ? null : (a[i] - a[i - 1]) * 100);
    const bloque = (tit, grande, fino, aviso) => `<div class="fb${aviso ? ' aviso' : ''}"><span class="fc"><span class="fh">${esc(tit)}</span><span class="fg">${grande}</span></span><span class="ff">${fino}</span></div>`;
    if (R.canales.length > 1) {
      const cols = colores(R.canales.length);
      partes.push('<div class="fb ancho" title="Monto · % de la venta del período · cambio de ese % en pp · variación del monto contra la barra anterior"><span class="fh">Venta por canal</span>'
        + R.canales.map((c, j) => { const v = R.porCanal.get(c).v, sh = tot[i] ? v[i] / tot[i] : 0, sha = i && tot[i - 1] ? v[i - 1] / tot[i - 1] : null;
          return `<span class="fcan"><i style="background:${cols[j]}"></i><b>${esc(c)}</b>S/ ${ent(v[i])} · ${p0(sh)}${span(txtPp(sha != null ? (sh - sha) * 100 : null, false))}${span(txtVar(vr(v)))}</span>`; }).join('') + '</div>');
    }
    const pprop = tot.map((t, j) => (t ? g.propina[j] / t : null));
    partes.push(bloque('Propinas', `S/ ${ent(g.propina[i])}${span(txtVar(vr(g.propina)))}`, `${p1(pprop[i] || 0)} de la venta${span(txtPp(pp(pprop), false))} · ${g.pax[i] ? `S/ ${U.dos(g.propina[i] / g.pax[i])}/cliente · ` : ''}${g.n_prop[i]} pagos`));
    const pdesc = g.carta.map((c, j) => (c ? g.desc[j] / c : null));
    if (pdesc[i] != null) partes.push(bloque('Descuentos', `${p1(pdesc[i])}${span(txtPp(pp(pdesc)))}`, `S/ ${ent(g.desc[i])} bajo la carta${g.n_docs[i] ? ` · ${g.n_desc[i]} de ${g.n_docs[i]} comprobantes` : ''}`));
    const pcort = g.carta.map((c, j) => (c ? g.cort_s[j] / c : null));
    if (pcort[i] != null) partes.push(bloque('Cortesías', `${p1(pcort[i])}${span(txtPp(pp(pcort)))}`, `${g.n_cort[i]} comp. · S/ ${ent(g.cort_s[i])} a carta${g.costo_cort[i] ? ` · costaron S/ ${ent(g.costo_cort[i])}` : ''}`));
    const pc = g.pcosto[i];
    if (pc != null) {
      let fino = `S/ ${ent(g.costo[i])} sobre S/ ${ent(g.neto[i])} de neto`;
      if (g.venta_sin_costo[i]) fino += ` · ${p0(g.venta_sin_costo[i] / tot[i])} de la venta sin costo cargado`;
      const ig = R.igv.get(k); if (ig) fino += ' · ' + U.marcaIgv(ig[1], ig[2]);
      partes.push(bloque('Costo', `${p1(pc)}${span(txtPp(pp(g.pcosto)))}`, fino, pc > K.COSTO_ROTO));
    }
    let aviso = '';
    const cu = R.culpables.get(k);
    if (pc != null && pc > K.COSTO_ROTO && cu) aviso += `<span class="rev">Revisar «${esc(cu.prod)}»: costo S/ ${U.dos(cu.pc)} por unidad contra precio S/ ${U.dos(cu.po)}</span>`;
    const sp = R.sinCostoProds.get(k); if (sp && sp.length) aviso += `<span class="sinc">Sin costo: ${esc(U.detalleSinCosto(sp, 3))}</span>`;
    const ig = R.igv.get(k); if (ig) aviso += `<span class="igv">${esc(U.notaIgv(ig[0], ig[1], ig[2], i && g.pcosto[i - 1] != null ? g.pcosto[i - 1] : pc))}</span>`;
    partes.push(`<div class="fpie">${aviso}<button class="fver" data-acc="verped" data-v="${esc(k)}">Ver pedidos de ${esc(R.fila[i])} →</button></div>`);
    return partes.join('');
  }
  function celda(c, tipo) {
    if (!c) return '<td></td>';
    if (tipo === 'var') return `<td class="r"><b style="color:${c.color}">${esc(c.t)}</b></td>`;
    if (tipo === 'texto') return `<td class="tx" title="${esc(c.tip || c.t)}">${esc(c.t)}</td>`;
    if (tipo !== 'celda') return `<td class="r">${esc(c.t)}</td>`;
    const bar = c.bar && fin(c.bar.w) ? ` style="--w:${(Math.max(0, Math.min(1, c.bar.w)) * 100).toFixed(1)}%"` : '';
    return `<td class="r"><span class="cv ${c.cls || ''}${bar ? ' bar ' + (c.bar.tono || '') : ''}"${bar}>${esc(c.t)}</span>`
      + `${c.nota && c.nota[0] ? `<span class="n ${c.nota[1]}">${esc(c.nota[0])}</span>` : ''}${c.band ? '<span class="band">revisar</span>' : ''}</td>`;
  }
  function tablaResumen(R, st) {
    const subs = subvistas(R), sub = subs[st.sub] ? st.sub : 'Venta', [cols] = subs[sub];
    let filas = filasResumen(R);
    if (st.orden) { const { col, dir } = st.orden; filas = filas.slice().sort((a, b) => { const x = a[col]?.v ?? -1e18, y = b[col]?.v ?? -1e18; return (x < y ? -1 : x > y ? 1 : 0) * dir; }); }
    const tot = totalResumen(R), rotP = { Día: 'Día', Semana: 'Semana', Mes: 'Mes', Año: 'Año' }[R.gran];
    const th = (campo, rot, _ancho, tip, der) => `<th class="${der ? 'r' : ''}" title="${esc(tip)}" data-acc="orden" data-v="${campo}">${esc(rot)}${st.orden && st.orden.col === campo ? (st.orden.dir > 0 ? ' ↑' : ' ↓') : ''}</th>`;
    // Como AG Grid (sizeColumnsToFit): los anchos declarados son PROPORCIONES y la tabla llena la tarjeta.
    const suma = 132 + cols.reduce((x, c) => x + c[3], 0), pc = (w) => `${(w / suma * 100).toFixed(2)}%`;
    let h = `<table class="tr"><colgroup><col style="width:${pc(132)}">${cols.map((c) => `<col style="width:${pc(c[3])}">`).join('')}</colgroup><thead><tr>${th('periodo', rotP, 120, '', false)}${cols.map((c) => th(c[0], c[1], c[3], c[4], c[2] !== 'texto')).join('')}</tr></thead><tbody>`;
    filas.forEach((r) => {
      const ab = st.abierta === r.__k;
      h += `<tr class="${ab ? 'ab' : ''}${st.foco === r.__k ? ' sel' : ''}" data-acc="fila" data-v="${esc(r.__k)}"><td title="${esc(r.periodo.tip || r.periodo.t)}">${esc(r.periodo.t)}${r.periodo.nota ? `<span class="n ${r.periodo.nota[1]}">${esc(r.periodo.nota[0])}</span>` : ''}</td>`
        + cols.map((c) => celda(r[c[0]], c[2])).join('') + '</tr>';
      if (ab) h += `<tr class="fr"><td colspan="${cols.length + 1}"><div class="franja">${franja(R, r.__i)}</div></td></tr>`;
    });
    h += `</tbody><tfoot><tr><td>${esc(tot.periodo)}</td>${cols.map((c) => `<td class="${c[2] === 'texto' ? 'tx' : 'r'}">${esc(tot[c[0]] ?? '')}</td>`).join('')}</tr></tfoot></table>`;
    return { html: h, ayuda: subs[sub][1], subs: Object.keys(subs) };
  }

  // ── El Detalle: pedidos (o meseros, servicios, comprobantes) y platos ──
  function detalle(B, R, st, M) {
    const ks = focoClaves(R, st);
    const amb = R.tabla.filter((l) => ks.includes(l.k));
    const lin0 = lineasPara(B, amb, st);   // null: no están, se pidieron
    const ver = st.ver;
    const q = M ? U.sinTildes(st.q || '').trim() : '';
    const pedNombre = (d) => (d.clase === K.NC ? `${d.ped} · NC` : String(d.ped));
    const grupoDe = { Mesero: (d) => d.mesero || 'Sin mesero', Servicio: (d) => d.serv || 'Sin servicio' };
    const filaDe = (l) => (ver === 'Pedido' ? pedNombre(l.doc) : ver === 'Comprobante' ? String(l.doc.i) : grupoDe[ver](l.doc));
    const sel = st.ped && st.pedVer === ver ? st.ped : null;
    let izq, totIzq, cab, cols;
    if (ver === 'Mesero' || ver === 'Servicio') {
      const g = new Map();
      amb.forEach((l) => { const k = filaDe(l); if (!g.has(k)) g.set(k, { nombre: k, venta: 0, peds: new Set(), lin: [] }); const e = g.get(k); e.venta += l.venta; if (l.doc.clase === K.VENTA) e.peds.add(l.doc.ped); e.lin.push(l); });
      const pax = V.paxPor(amb, filaDe), canCli = new Set(amb.filter((l) => l.doc.pax > 0).map((l) => l.doc.canal));
      const prop = new Map();
      if (ver === 'Mesero') R.propMesero.filter((p) => ks.includes(p.k)).forEach((p) => { const k = p.mesero || 'Sin mesero'; prop.set(k, (prop.get(k) || 0) + p.prop); });
      const tot = [...g.values()].reduce((s, e) => s + e.venta, 0);
      let rows = [...g.values()].map((e) => { const px = pax.get(e.nombre) || 0, vc = e.lin.filter((l) => canCli.has(l.doc.canal)).reduce((s, l) => s + l.venta, 0);
        return { k: e.nombre, nombre: e.nombre, pedidos: e.peds.size, pax: px, venta: e.venta, pct: tot ? e.venta / tot : null, ticket: px ? vc / px : null, propina: prop.get(e.nombre) || 0 }; })
        .sort((a, b) => b.venta - a.venta || (a.nombre < b.nombre ? -1 : 1));
      if (q) { const conPlato = new Set((lin0 || []).filter((l) => U.sinTildes(l.prod).includes(q)).map(filaDe)); rows = rows.filter((r) => conPlato.has(r.k) || U.sinTildes(r.nombre).includes(q)); }
      cols = [['nombre', ver, '', 0], ['pedidos', 'Pedidos', 'r', 64], ['pax', 'Pax', 'r', 48], ['venta', 'Venta', 'r', 84], ['pct', '%', 'r', 56], ['ticket', 'Ticket', 'r', 66]];
      if (ver === 'Mesero') cols.push(['propina', 'Propina', 'r', 72]);
      izq = rows.map((r) => ({ k: r.k, sel: r.k === sel, v: r, c: { nombre: esc(r.nombre), pedidos: ent(r.pedidos), pax: ent(r.pax), venta: s0(r.venta), pct: r.pct != null ? p1(r.pct) : '', ticket: fin(r.ticket) ? s0(r.ticket) : '—', propina: s0(r.propina) } }));
      const pxT = rows.reduce((s, r) => s + r.pax, 0), vcT = amb.filter((l) => canCli.has(l.doc.canal)).reduce((s, l) => s + l.venta, 0);
      totIzq = { nombre: `Total · ${rows.length} ${ver === 'Mesero' ? 'mesero' : 'servicio'}${rows.length === 1 ? '' : 's'}`, pedidos: ent(rows.reduce((s, r) => s + r.pedidos, 0)), pax: ent(pxT),
        venta: s0(rows.reduce((s, r) => s + r.venta, 0)), pct: '100.0%', ticket: pxT ? s0(vcT / pxT) : '', propina: s0(rows.reduce((s, r) => s + r.propina, 0)) };
      cab = cols;
    } else {
      const g = new Map();
      amb.forEach((l) => {
        const k = filaDe(l), d = l.doc;
        if (!g.has(k)) g.set(k, { k, d, ini: Infinity, fin: -Infinity, platos: 0, valor: 0, pax: -Infinity, abre: null });
        const e = g.get(k); e.ini = Math.min(e.ini, d.emision); e.fin = Math.max(e.fin, d.emision); e.platos += l.n; e.valor += l.venta; e.pax = Math.max(e.pax, d.pax);
        const ap = B.pedidos[d.ped][1]; if (ap != null) e.abre = e.abre == null ? ap : Math.min(e.abre, ap);
      });
      let rows = [...g.values()].sort((a, b) => b.valor - a.valor || (a.k < b.k ? -1 : 1));
      const dia = (m) => { const [y, mo, dd] = U.ymd(B.base + Math.floor(m / 1440)); void y; return `${String(dd).padStart(2, '0')}/${String(mo).padStart(2, '0')}`; };
      const hora = (m) => (R.gran === 'Día' && ks.length === 1 ? U.hhmm(m) : `${dia(m)} ${U.hhmm(m)}`);
      if (q) {
        const conPlato = new Set((lin0 || []).filter((l) => U.sinTildes(l.prod).includes(q)).map(filaDe));
        rows = rows.filter((r) => conPlato.has(r.k) || U.sinTildes(`${B.pedidos[r.d.ped][0]} ${r.d.mesero} ${V.numeroSunat(r.d.num)} ${r.d.canal}`).includes(q));
      }
      const variosCanales = new Set(amb.map((l) => l.doc.canal)).size > 1;
      if (ver === 'Comprobante') {
        cols = [['hora', 'Hora', '', R.gran === 'Día' && ks.length === 1 ? 48 : 90], ['comp', 'Comprobante', '', 150], ['mesero', 'Mesero', '', 0], ...(variosCanales ? [['canal', 'Canal', '', 78]] : []), ['platos', 'Platos', 'r', 46], ['valor', 'Valor', 'r', 84]];
        const nnc = rows.filter((r) => r.d.clase === K.NC).length;
        izq = rows.map((r) => ({ k: r.k, sel: r.k === sel, v: { hora: r.ini, valor: r.valor, platos: r.platos }, c: { hora: hora(r.ini), comp: esc(`${U.tipoCorto(r.d.tdoc, r.d.clase)} ${V.numeroSunat(r.d.num)}`.trim() + (r.d.porCobrar ? ' · por cobrar' : '')), mesero: esc(r.d.mesero || '—'), canal: esc(r.d.canal), platos: ent(r.platos), valor: s2(r.valor) } }));
        totIzq = { hora: 'Total', comp: `${rows.length - nnc} comprobante${rows.length - nnc === 1 ? '' : 's'}${nnc ? ` · ${nnc} NC` : ''}`, platos: ent(rows.reduce((s, r) => s + r.platos, 0)), valor: s2(rows.reduce((s, r) => s + r.valor, 0)) };
      } else {
        cols = [['pedido', 'Pedido', '', 84], ['horario', 'Horario', '', R.gran === 'Día' && ks.length === 1 ? 92 : 124], ['tiempo', 'Tiempo', 'r', 58], ['mesero', 'Mesero', '', 0], ...(variosCanales ? [['canal', 'Canal', '', 78]] : []), ['docn', 'Doc.', '', 96], ['pax', 'Pax', 'r', 34], ['valor', 'Valor', 'r', 76]];
        const minutos = (r) => (r.d.clase === K.NC || r.abre == null || r.fin < r.abre ? null : Math.round(r.fin - r.abre));
        const fmtT = (m) => (m == null ? '' : m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}`);
        izq = rows.map((r) => ({ k: r.k, sel: r.k === sel, v: { pedido: B.pedidos[r.d.ped][0], horario: r.abre ?? r.ini, tiempo: minutos(r), pax: Math.max(0, r.pax), valor: r.valor },
          tip: `${U.tipoCorto(r.d.tdoc, r.d.clase)} ${V.numeroSunat(r.d.num, true)}`,
          c: { pedido: esc(B.pedidos[r.d.ped][0] || r.k), horario: r.abre != null ? `${hora(r.abre)}–${U.hhmm(r.fin)}` : hora(r.fin), tiempo: fmtT(minutos(r)), mesero: esc(r.d.mesero || '—'), canal: esc(r.d.canal), docn: esc(V.numeroSunat(r.d.num)), pax: ent(Math.max(0, r.pax)), valor: s0(r.valor) } }));
        const med = U.mediana(rows.filter((r) => r.pax > 0).map(minutos));
        totIzq = { pedido: 'Total', mesero: `${rows.length} pedido${rows.length === 1 ? '' : 's'}`, tiempo: fmtT(med == null ? null : Math.round(med)), pax: ent(rows.reduce((s, r) => s + Math.max(0, r.pax), 0)), valor: s0(rows.reduce((s, r) => s + r.valor, 0)) };
      }
      cab = cols;
    }
    // Orden del usuario en la tabla de la izquierda.
    if (st.ordenDet) { const { col, dir } = st.ordenDet; izq = izq.slice().sort((a, b) => { const x = a.v[col] ?? '', y = b.v[col] ?? ''; return (x < y ? -1 : x > y ? 1 : 0) * dir; }); }
    // Los platos: del elegido o del período entero.
    const lin = lin0 == null ? [] : sel == null ? lin0 : lin0.filter((l) => filaDe(l) === sel);
    const agrupar = sel == null || ver === 'Mesero' || ver === 'Servicio';
    let platos;
    if (agrupar) {
      const m = new Map();
      lin.forEach((l) => { const e = m.get(l.prod) || { prod: l.prod, cant: 0, venta: 0 }; e.cant += l.cant; e.venta += l.venta; m.set(l.prod, e); });
      platos = [...m.values()].filter((e) => Math.round(e.cant * 1000) || Math.round(e.venta * 100));
    } else platos = lin.map((l) => ({ prod: l.prod, cant: l.cant, venta: l.venta }));
    if (q) platos = platos.filter((p) => U.sinTildes(p.prod).includes(q) || sel != null);
    platos.sort((a, b) => b.venta - a.venta);
    const thI = cab.map(([c, r, al]) => `<th class="${al}" data-acc="ordendet" data-v="${c}">${esc(r)}${st.ordenDet && st.ordenDet.col === c ? (st.ordenDet.dir > 0 ? ' ↑' : ' ↓') : ''}</th>`).join('');
    const colg = (cs) => `<colgroup>${cs.map((c) => `<col style="width:${c[3] ? c[3] + 'px' : 'auto'}">`).join('')}</colgroup>`;
    const tIzq = `<table class="td">${colg(cab)}<thead><tr>${thI}</tr></thead><tbody>${izq.map((r) => `<tr class="${r.sel ? 'sel' : ''}" data-acc="ped" data-v="${esc(r.k)}"${r.tip ? ` title="${esc(r.tip)}"` : ''}>${cab.map(([c, , al]) => `<td class="${al}">${r.c[c] ?? ''}</td>`).join('')}</tr>`).join('')}</tbody>`
      + `<tfoot><tr>${cab.map(([c, , al]) => `<td class="${al}">${esc(totIzq[c] ?? '')}</td>`).join('')}</tr></tfoot></table>`;
    const tLin = `<table class="td">${colg([['', '', '', 0], ['', '', '', 62], ['', '', '', 76], ['', '', '', 86]])}<thead><tr><th>Producto</th><th class="r">Cantidad</th><th class="r">P. unit.</th><th class="r">Valor</th></tr></thead><tbody>${lin0 == null ? '<tr><td colspan="4" class="cargando">Trayendo los platos de esos días…</td></tr>' : ''}${platos.map((p) => `<tr><td title="${esc(p.prod)}">${esc(p.prod)}</td><td class="r">${+p.cant.toFixed(3)}</td><td class="r">${p.cant ? s2(p.venta / p.cant) : ''}</td><td class="r">${s2(p.venta)}</td></tr>`).join('')}</tbody>`
      + `<tfoot><tr><td>Total · ${platos.length} plato${platos.length === 1 ? '' : 's'}</td><td class="r">${agrupar ? ent(platos.reduce((s, p) => s + p.cant, 0)) : ''}</td><td></td><td class="r">${s2(platos.reduce((s, p) => s + p.venta, 0))}</td></tr></tfoot></table>`;
    const uno = { Pedido: 'un pedido', Mesero: 'un mesero', Servicio: 'un servicio', Comprobante: 'un comprobante' }[ver];
    const elegido = { Pedido: 'del pedido elegido', Mesero: `que vendió ${sel}`, Servicio: `de ${String(sel).toLowerCase()}`, Comprobante: 'del comprobante elegido' }[ver];
    const pie = `<b>${esc(nombreFoco(R, st))}</b> — ${sel == null ? `al costado, todos los platos del período. Clic en ${uno} para ver sólo los suyos.` : `al costado, los platos ${esc(elegido)}. Otro clic en la fila vuelve a todos los del período.`}`;
    return { html: `<div class="det"><div class="dt">${tIzq}</div><div class="dt">${tLin}</div></div>`, pie, izq, platos, cab };
  }

  function lineasPara(B, amb, st) {
    if (!amb.length) return [];
    let a = Infinity, b = -Infinity;
    amb.forEach((u) => { a = Math.min(a, u.doc.dia); b = Math.max(b, u.doc.dia); });
    let pool = null;
    if (a >= B.lineasDesde) pool = B.lineas;
    else if (B.extra && a >= B.extra.desde && b <= B.extra.hasta) pool = B.extra.lineas;
    if (!pool) { pedirLineas(a - B.base, b - B.base); return null; }
    const docs = new Set(amb.map((u) => u.doc.i));
    return pool.filter((l) => docs.has(l.doc.i) && V.pasaFiltros(st.fil, l.grupo, l.doc)
      && (l.doc.clase === K.VENTA || l.doc.clase === K.NC));
  }
  function pedirLineas(desde, hasta) {
    const G = window.__vtPeriodo;
    if (G.pedido && G.pedido.desde === desde && G.pedido.hasta === hasta) return;
    G.pedido = { desde, hasta };
    if (G.enviar) G.enviar('lineas', { sello: G.sello, desde, hasta, n: Date.now() });
  }

  // El Excel de lo que se ve: el Resumen con su subvista, o el Detalle con sus platos.
  const plano = (h) => String(h ?? '').replace(/<[^>]*>/g, '').replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
  function excel(raiz) {
    const S = raiz.__vp, st = S.st, R = S.R;
    if (!R) return;
    const rango = `${U.iso(R.rngDatos[0])}_${U.iso(R.rngDatos[1])}`;
    let hojas, nombre;
    if (st.modo === 'Resumen') {
      const subs = subvistas(R), sub = subs[st.sub] ? st.sub : 'Venta', [cols] = subs[sub];
      const val = (c, tipo) => {
        if (!c) return null;
        if (tipo === 'texto') return c.t;
        if (!fin(c.v)) return c.t === '—' ? null : c.t;
        return String(c.t).endsWith('%') ? Math.round(c.v * 10000) / 100 : c.v;
      };
      const filas = filasResumen(R).map((r) => [r.periodo.t, ...cols.map((c) => val(r[c[0]], c[2]))]);
      hojas = [{ nombre: `Resumen ${sub}`, cabeza: [R.gran, ...cols.map((c) => c[1] + (c[2] === 'celda' && /%/.test(c[1]) ? '' : ''))], filas }];
      nombre = `venta_por_periodo_${archivo(sub)}_${rango}.xlsx`;
    } else if (S.det && focoClaves(R, st)) {
      const d = S.det;
      hojas = [{ nombre: st.ver, cabeza: d.cab.map((c) => c[1]), filas: d.izq.map((r) => d.cab.map(([c]) => (fin(r.v[c]) && c !== 'horario' && c !== 'hora' ? r.v[c] : plano(r.c[c])))) },
        { nombre: 'Platos', cabeza: ['Producto', 'Cantidad', 'Precio unitario', 'Venta'], filas: d.platos.map((p) => [p.prod, p.cant, p.cant ? p.venta / p.cant : null, p.venta]) }];
      nombre = `venta_por_periodo_detalle_${archivo(nombreFoco(R, st))}.xlsx`;
    } else { st.aviso = 'Elegí una barra para bajar su Detalle.'; render(raiz); return; }
    bajar(nombre, libro(hojas));
  }

  // ── La raíz ─────────────────────────────────────────────────────────────
  function render(raiz) {
    const S = raiz.__vp, st = S.st, B = S.B, M = S.mejoras;
    const R = V.calcular(B, st);
    S.R = R;
    raiz.classList.toggle('m', !!M);
    if (!R) { raiz.innerHTML = '<div class="vacio">No hay ventas para los filtros elegidos.</div>'; return; }
    if (st.foco && !R.claves.includes(st.foco)) st.foco = null;
    if (st.tramo && (st.tramo[1] >= R.n)) st.tramo = null;
    const conTabla = st.modo === 'Resumen' || !!focoClaves(R, st);
    const ancho = (raiz.clientWidth || 1159);
    const alto = conTabla ? B.alto.fig : B.alto.figSolo;
    const gr = grafico(R, st, ancho, alto, M);
    S.X = gr.X; S.W = gr.W;
    const tit = { Día: 'Tendencia diaria de venta', Semana: 'Venta por semana', Mes: 'Venta por mes', Año: 'Venta por año' }[R.gran];
    const fil = FIL.map(([k, rot]) => {
      const sel = st.fil[k], ops = B.opciones[k];
      return `<div class="ms"><button class="ms-b${sel.length ? ' on' : ''}" data-acc="menu" data-v="${k}">${esc(sel.length ? `${rot}: ${sel.length === 1 ? sel[0] : sel.length + ' elegidos'}` : `${rot}: todos`)} <i>▾</i></button>`
        + (st.menu === k ? `<div class="ms-l">${ops.map((o) => `<label><input type="checkbox" data-acc="filtro" data-k="${k}" data-v="${esc(o)}" ${sel.includes(o) ? 'checked' : ''}> ${esc(o)}</label>`).join('')}${sel.length ? '<button class="ms-x" data-acc="limpiar" data-v="' + k + '">Quitar el filtro</button>' : ''}</div>` : '') + '</div>';
    }).join('');
    let zona = '', pie = '', ctrl2 = '';
    let ayuda = '';
    if (st.modo === 'Resumen') {
      const t = tablaResumen(R, st);
      if (!t.subs.includes(st.sub)) st.sub = 'Venta';
      ctrl2 = `<div class="seg">${t.subs.map((x) => `<button class="${x === st.sub ? 'on' : ''}" data-acc="sub" data-v="${x}">${x}</button>`).join('')}</div>`;
      zona = `<div class="zr" style="height:${B.alto.tabla}px">${t.html}</div>`;
      ayuda = t.ayuda;
      pie = `<b>${esc(U.delAl(R.rngDatos[0], R.rngDatos[1]))}</b> · ${esc(t.ayuda)}${esc(R.nota)}`;
    } else {
      ctrl2 = `<div class="seg">${K.VER_POR.map((x) => `<button class="${x === st.ver ? 'on' : ''}" data-acc="ver" data-v="${x}">${x}</button>`).join('')}</div>`;
      if (focoClaves(R, st)) {
        const d = detalle(B, R, st, M);
        zona = (M ? `<div class="busca"><input id="vp-busca" data-acc="buscar" placeholder="Buscar un pedido, mesero, comprobante o plato…" value="${esc(st.q)}">${NUEVO}</div>` : '')
          + `<div class="zr det-w" style="height:${B.alto.tabla}px">${d.html}</div>`;
        pie = d.pie;
        S.det = d;
      } else pie = M ? 'Tocá una barra —o arrastrá sobre varias— para ver sus pedidos.' : 'Tocá una barra —o una fila del Resumen— para ver sus pedidos.';
    }
    const nombres = { Venta: 'Venta documentada', Costo: 'Costo histórico de lo vendido', Pagos: 'Pagos registrados de comprobantes', Cuadre: 'Conciliación de venta documentada', 'Cortesías': 'Cortesías y su costo histórico', Descuentos: 'Descuentos sobre precio de carta', Propinas: 'Propinas de los comprobantes seleccionados' };
    const sub = st.modo === 'Resumen' ? st.sub : 'Detalle';
    const valores = sub === 'Pagos' ? 'Importes de pagos en soles' : sub === 'Costo' ? 'Neto sin IGV ni recargo' : 'Venta con impuestos · neto sin IGV ni recargo';
    const franja = Object.fromEntries((B.franja || []).map(([r, v]) => [r, v]));
    const sel = [['Grupos', st.fil.grupo.length ? st.fil.grupo : franja.Grupos || []], ['Subgrupos', franja.Subgrupos || []],
      ['Canales', st.fil.canal.length ? st.fil.canal : franja.Canales || []], ['Servicios', st.fil.serv.length ? st.fil.serv : franja.Servicios || []],
      ['Documentos', st.fil.tdoc]].filter(([, v]) => v.length).map(([r, v]) => `${r}: ${v.join(', ')}`);
    const ambito = sel.length ? sel.join(' · ') : 'Todos los grupos y canales';
    const baseF = B.turno ? 'Día del turno del comprobante' : 'Emisión del comprobante';
    void ayuda;
    raiz.innerHTML = `<div class="ctl"><div class="seg">${K.GRANOS.map((x) => `<button class="${x === st.gran ? 'on' : ''}" data-acc="gran" data-v="${x}">${x}</button>`).join('')}</div>`
      + `<div class="fils">${fil}</div><span class="lugar-fecha" aria-hidden="true"></span></div>`
      + `<div class="cab"><div class="kp"><span class="tit">${esc(tit)}</span><div class="kpis">${kpis(R, st, M)}</div>${M && st.modo === 'Detalle' && focoClaves(R, st) ? NUEVO : ''}</div><div class="ley">${leyenda(R, st)}</div></div>`
      + `<div class="gr" style="height:${alto}px">${gr.svg}<div class="tip" hidden></div></div>`
      + `<div class="pie"><div class="seg">${['Resumen', 'Detalle'].map((x) => `<button class="${x === st.modo ? 'on' : ''}" data-acc="modo" data-v="${x}">${x}</button>`).join('')}</div>${ctrl2}<span class="pt">${pie}</span>`
      + (M ? `<button class="excel" data-acc="excel">Excel ${NUEVO}</button>` : '') + '</div>'
      + `<div class="ctx"><span>${esc(nombres[sub] || 'Venta documentada')} · ${esc(baseF)} · ${esc(valores)} · ${esc(ambito)}</span><button class="como" data-acc="como">ⓘ Cómo se calcula ▾</button>`
      + (st.como ? `<div class="como-p">${COMO.replace('día del turno del comprobante', baseF.toLowerCase())}</div>` : '') + '</div>'
      + zona + (st.aviso ? `<div class="aviso">${esc(st.aviso)}</div>` : '');
    const b = raiz.querySelector('#vp-busca');
    if (b && S.enfocarBusca) { b.focus(); b.setSelectionRange(b.value.length, b.value.length); S.enfocarBusca = false; }
  }
  const COMO = '<b>Fecha y alcance</b><p>Base temporal: día del turno del comprobante. Los filtros de esta vista se combinan con los de Ventas.</p>'
    + '<b>Venta documentada</b><p>Comprobantes pagados y por cobrar, menos notas de crédito. Cortesías y anulados se muestran aparte. «Venta» incluye impuestos y recargo; «Neto» los excluye. Cada ítem se cuenta una vez aunque tenga varias formas de pago.</p>'
    + '<b>Costo histórico de lo vendido</b><p>Costo guardado en el pedido, incluidos componentes de combos y propiedades, por la cantidad vendida. Las notas de crédito revierten el costo correspondiente. <b>% costo = costo histórico ÷ venta neta</b>. Es la valorización registrada al vender, distinta del costo actual de la carta.</p>'
    + '<b>Pagos registrados</b><p>Cada pago se suma una vez, en soles y con la propina aparte. Aquí se agrupan los pagos asociados a los comprobantes del período por la fecha del comprobante. «Por cobrar» refleja el estado de esos documentos en la última actualización. Las notas de crédito y canjes se concilian con la venta documentada en «Cuadre».</p>'
    + '<b>Referencias en Inforest</b><p><b>Registro de Ventas:</b> comprobantes y notas de crédito; para comparar por emisión, elegir «Emisión · SUNAT» en los filtros de Ventas. <b>Paloteo de Producción → Comparativo → Ventas en el rango:</b> referencia para el costo histórico. <b>Liquidación de Cajero:</b> referencia para pagos y cuentas por cobrar.</p>';

  function pintarTip(raiz, i) {
    const S = raiz.__vp, tip = raiz.querySelector('.tip');
    if (!tip) return;
    if (i == null) { tip.hidden = true; return; }
    tip.innerHTML = ficha(S.R, S.st, i);
    tip.hidden = false;
    const w = tip.offsetWidth || 260, x = S.X(i);
    tip.style.left = `${x + 14 + w <= S.W ? x + 14 : Math.max(0, x - 14 - w)}px`;
  }

  function accion(raiz, acc, el, ev) {
    const S = raiz.__vp, st = S.st, v = el.dataset.v, R = S.R;
    if (acc !== 'menu' && acc !== 'filtro' && acc !== 'limpiar') st.menu = null;
    if (acc === 'gran') { st.gran = v; st.foco = null; st.tramo = null; st.ped = null; st.abierta = null; st.orden = null; }
    else if (acc === 'menu') st.menu = st.menu === v ? null : v;
    else if (acc === 'filtro') { const k = el.dataset.k, a = st.fil[k]; st.fil[k] = el.checked ? [...a, v] : a.filter((x) => x !== v); st.foco = null; st.tramo = null; st.ped = null; }
    else if (acc === 'limpiar') { st.fil[v] = []; st.menu = null; }
    else if (acc === 'ley') st.ley = !st.ley;
    else if (acc === 'apagar') st.apag[v] = !el.checked;
    else if (acc === 'barra') {
      if (S.arrastre) return;
      const k = R.claves[+el.dataset.i];
      st.tramo = null;
      if (st.modo === 'Resumen') { st.ped = null; st.foco = k; st.modo = 'Detalle'; }
      else if (st.ped) { st.ped = null; st.foco = k; }
      else st.foco = st.foco === k ? null : k;
    } else if (acc === 'modo') { st.modo = v; st.aviso = ''; }
    else if (acc === 'sub') st.sub = v;
    else if (acc === 'ver') { st.ver = v; st.ped = null; st.ordenDet = null; }
    else if (acc === 'orden') { const o = st.orden; st.orden = !o || o.col !== v ? { col: v, dir: v === 'periodo' ? 1 : -1 } : o.dir === (v === 'periodo' ? 1 : -1) ? { col: v, dir: -o.dir } : null; st.abierta = null; }
    else if (acc === 'ordendet') { const o = st.ordenDet; st.ordenDet = !o || o.col !== v ? { col: v, dir: -1 } : o.dir < 0 ? { col: v, dir: 1 } : null; }
    else if (acc === 'fila') { if (ev.target.closest('.franja')) return; st.abierta = st.abierta === v ? null : v; }
    else if (acc === 'verped') { st.foco = v; st.tramo = null; st.ped = null; st.modo = 'Detalle'; }
    else if (acc === 'ped') { st.ped = st.ped === v && st.pedVer === st.ver ? null : v; st.pedVer = st.ver; }
    else if (acc === 'como') st.como = !st.como;
    else if (acc === 'excel') { excel(raiz); return; }
    else return;
    st.aviso = '';
    render(raiz);
  }
  function enlazar(raiz) {
    raiz.addEventListener('click', (ev) => {
      const el = ev.target.closest('[data-acc]');
      if (!el || !raiz.contains(el)) { if (ev.target.closest('.ms-l, .ley-p, .como-p')) return; if (raiz.__vp.st.menu) { raiz.__vp.st.menu = null; render(raiz); } return; }
      if (el.dataset.acc === 'buscar' || (el.dataset.acc === 'filtro' && ev.type === 'click' && el.tagName !== 'INPUT')) return;
      accion(raiz, el.dataset.acc, el, ev);
    });
    raiz.addEventListener('input', (ev) => {
      if (ev.target.dataset.acc === 'buscar') { raiz.__vp.st.q = ev.target.value; raiz.__vp.enfocarBusca = true; render(raiz); }
    });
    raiz.addEventListener('mouseover', (ev) => { const b = ev.target.closest('[data-acc="barra"]'); if (b) { pintarTip(raiz, +b.dataset.i); arrastrar(raiz, +b.dataset.i); } });
    raiz.addEventListener('mouseout', (ev) => { const b = ev.target.closest('[data-acc="barra"]'); if (b && !(ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest('[data-acc="barra"]'))) pintarTip(raiz, null); });
    // Mejoras: arrastrar sobre varias barras elige un TRAMO.
    raiz.addEventListener('mousedown', (ev) => {
      const b = ev.target.closest('[data-acc="barra"]');
      if (!b || !raiz.__vp.mejoras) return;
      raiz.__vp.drag = { a: +b.dataset.i, b: +b.dataset.i };
      ev.preventDefault();
    });
    window.addEventListener('mouseup', () => {
      const S = raiz.__vp, d = S.drag;
      if (!d) return;
      S.drag = null;
      if (d.a !== d.b) {
        S.st.tramo = [Math.min(d.a, d.b), Math.max(d.a, d.b)]; S.st.foco = null; S.st.ped = null; S.st.modo = 'Detalle';
        S.arrastre = true; render(raiz); setTimeout(() => { S.arrastre = false; }, 0);
      }
    });
  }
  function arrastrar(raiz, i) {
    const S = raiz.__vp;
    if (!S.drag || S.drag.b === i) return;
    S.drag.b = i;
    raiz.querySelectorAll('.hit').forEach((r) => { const j = +r.dataset.i; r.classList.toggle('tr', j >= Math.min(S.drag.a, i) && j <= Math.max(S.drag.a, i)); });
  }

  window.__vpUI = { render, enlazar, estadoInicial };
}());

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.parte) return;
  const G = window.__vtPeriodo || (window.__vtPeriodo = { st: null });
  const UI = window.__vpUI;
  if (data.parte === 'lineas') {
    // Las líneas pedidas de un período viejo: se suman y se vuelve a dibujar.
    if (G.B && data.sello === G.sello && !(G.lineasDe === `${data.desde}-${data.hasta}`)) {
      G.lineasDe = `${data.desde}-${data.hasta}`;
      G.B.extra = { desde: G.B.base + data.desde, hasta: G.B.base + data.hasta, lineas: data.lineas.map(G.B.linea) };
      G.pedido = null;
      if (G.raiz && G.raiz.isConnected) UI.render(G.raiz);
    }
    return;
  }
  let raiz = parentElement.querySelector('.vp');
  const nueva = !raiz;
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'vp';
    parentElement.appendChild(raiz);
    raiz.__vp = G;
    UI.enlazar(raiz);
    let ancho = 0;
    new ResizeObserver(() => { if (Math.abs(raiz.clientWidth - ancho) > 2) { ancho = raiz.clientWidth; if (G.B) UI.render(raiz); } }).observe(raiz);
  }
  raiz.__vp = G;
  G.raiz = raiz;
  G.enviar = setTriggerValue;
  // La fecha es un botón de Python en la misma página (sin iframe): la fila de
  // controles le deja exactamente su ancho, que cambia con el atajo elegido.
  const fb = document.querySelector('.st-key-vt_periodo_fecha');
  if (fb && fb.offsetWidth) raiz.style.setProperty('--vp-fecha', `${fb.offsetWidth + 12}px`);
  G.mejoras = true;
  if (!G.st) G.st = UI.estadoInicial();
  const ctx = JSON.stringify([data.sello, data.turno, data.franja]);
  if (G.sello !== data.sello) {
    G.B = window.VentasPeriodo.preparar(data);
    G.sello = data.sello;
    G.pedido = null; G.lineasDe = null;
    G.st.ped = null; G.st.abierta = null; G.st.tramo = null;
  } else if (!nueva && G.ctx === ctx) {
    // La MISMA vista de la corrida anterior (el fragment se vuelve a correr
    // al pedir líneas): redibujar costaba ~0,6 s con doce meses y no cambia nada.
    return;
  }
  G.ctx = ctx;
  G.B.turno = data.turno !== false; G.B.franja = data.franja || [];
  UI.render(raiz);
}
