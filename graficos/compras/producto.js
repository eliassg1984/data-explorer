// Compras › Producto (reglas #713 y #774).
//
// La monta graficos/compras/producto.py con st.components.v2 (sin iframe,
// estilos en un shadow root) DOS VECES: `parte: "ficha"` trae el historial de
// líneas y no dibuja nada; `parte: "rank"` trae el resumen del rango, y dibuja
// la pantalla. Así cambiar la fecha no vuelve a mandar el historial.
// `_xlsx.js` y `lista_ficha.js` van antepuestos.
//
// `window.__cpProd` guarda los datos de los dos montajes y lo elegido: sobrevive
// a que Streamlit vuelva a montar la pieza (cambiar de reporte y volver). A Python
// vuelven sólo la fecha (un botón suyo, en el hueco de la cabecera) y el menú de
// familias, que es el filtro de la página.
//
// Las cuentas son las de producto.py (`_resumen`, `_serie`, `_precios`,
// `periodo.ventana`, `tramo_parcial`): si se toca una, se toca la otra. Lo
// vigila test_producto_pieza.py, que corre `serie` en Chromium contra
// `_serie` de Python.

const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIA = 864e5;
// La fila de un producto del ranking y la de un grupo (producto.armar_ranking).
const RP = { i: 0, fam: 1, sub: 2, um: 3, valor: 4, cant: 5, var: 6, est: 7, pp: 8, hab: 9, ppv: 10, nflag: 11,
  docs: 12, ult: 13, ultp: 14, cada: 15, prev: 16, vref: 17, refc: 18 };
// Una línea del historial (producto.historial_pieza).
const RL = { dia: 0, prov: 1, doc: 2, cant: 3, valor: 4, ref: 5, flag: 6 };
const FLAGS = ['', 'um', 'precio'];
const GRANOS = [['Semana', 'Semana'], ['Mes', 'Mes'], ['Año', 'Año'], ['Documento', 'Documento']];
const OPS = [['Rango', 'el rango'], ['3m', '3 meses'], ['12m', '12 meses'], ['24m', '24 meses'], ['Todo', 'todo']];
const MESES_OP = { '3m': 3, '12m': 12, '24m': 24 };
const FILAS_TIP = 5;

// ── Fechas como número de día (UTC) ──────────────────────────────────────
const dn = (s) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d) / DIA; };
const ymd = (n) => { const t = new Date(n * DIA); return [t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()]; };
const iso = (n) => { const [y, m, d] = ymd(n); return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
const diaSemana = (n) => (new Date(n * DIA).getUTCDay() + 6) % 7;
const fCorta = (n) => { const [, m, d] = ymd(n); return `${d} ${MES[m - 1]}`; };

// ── Formato (los de producto.py) ─────────────────────────────────────────
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const finito = (v) => v != null && isFinite(v);
const ent = (v) => Math.round(v).toLocaleString('en-US');
const soles = (v) => (finito(v) ? `${v < -0.5 ? '−' : ''}S/ ${ent(Math.abs(v))}` : '—');
const precio = (v) => (finito(v) ? `S/ ${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—');
function cant(c, um) {
  if (!finito(c)) return '—';
  const t = Math.abs(c) < 100
    ? c.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).replace(/\.0$/, '')
    : ent(c);
  return um ? `${t} ${um}` : t;
}
const varPct = (cur, prev) => (finito(prev) && prev > 0 && finito(cur) ? (cur - prev) / prev * 100 : null);
const fmtVar = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.05 ? '0 %' : `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(1)} %`);
const solesG = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.5 ? 'S/ 0' : `${v > 0 ? '+' : '−'}S/ ${ent(Math.abs(v))}`);
const colorPpv = (v) => (!finito(v) || Math.abs(v) < 1 ? '' : v > 0 ? 'rojo' : 'verde');
const colorPrecio = (v) => (!finito(v) || Math.abs(v) < 0.2 ? '' : v > 0 ? 'rojo' : 'verde');
const tramo = (a, b) => { const x = ymd(a), y = ymd(b); return x[1] === y[1] ? `${x[2]}–${y[2]} ${MES[y[1] - 1]}` : `${fCorta(a)} – ${fCorta(b)}`; };
const clsVar = (v) => (!finito(v) || Math.abs(v) < 0.5 ? 'igual' : v > 0 ? 'sube' : 'baja');
const trunc = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
const sinTildes = (s) => String(s).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
// El buscador (regla #581): cada PALABRA tiene que estar, en cualquier orden.
const coincide = (nom, q) => sinTildes(q).split(/\s+/).filter(Boolean).every((p) => sinTildes(nom).includes(p));

// ── Los períodos de la curva (producto._clave, _secuencia, _etq) ────────
function clave(n, gran) {
  const [y, m] = ymd(n);
  if (gran === 'Mes') return `${y}-${String(m).padStart(2, '0')}`;
  if (gran === 'Semana') return iso(n - diaSemana(n));
  return String(y);
}
function inicioDe(n, gran) {
  const [y, m] = ymd(n);
  if (gran === 'Mes') return Date.UTC(y, m - 1, 1) / DIA;
  if (gran === 'Semana') return n - diaSemana(n);
  if (gran === 'Año') return Date.UTC(y, 0, 1) / DIA;
  return n;
}
function secuencia(ini, fin, gran) {
  const out = [];
  if (gran === 'Mes') {
    let [y, m] = ymd(ini); const [yf, mf] = ymd(fin);
    while (y < yf || (y === yf && m <= mf)) { out.push(`${y}-${String(m).padStart(2, '0')}`); m += 1; if (m > 12) { m = 1; y += 1; } }
    return out;
  }
  if (gran === 'Semana') { for (let x = ini - diaSemana(ini); x <= fin; x += 7) out.push(iso(x)); return out; }
  for (let y = ymd(ini)[0]; y <= ymd(fin)[0]; y += 1) out.push(String(y));
  return out;
}
// `fin - DateOffset(months=k)`: el mismo día, o el último del mes si no existe.
function restarMeses(n, k) {
  const [y, m, d] = ymd(n);
  const t = new Date(Date.UTC(y, m - 1 - k, 1));
  const ult = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth() + 1, 0)).getUTCDate();
  return Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), Math.min(d, ult)) / DIA;
}
// periodo.ventana: contada desde el último día CON DATOS, +1 día.
function ventana(op, ultimo, minimo, rango) {
  if (op === 'Rango') return rango;
  if (op === 'Todo') return [Math.min(minimo, ultimo), ultimo];
  let ini = restarMeses(ultimo, MESES_OP[op]) + 1;
  if (minimo > ini) ini = minimo;
  return [ini, ultimo];
}
// _comun.tramo_parcial: el último período, si está a medias.
function parcial(gran, u) {
  const [y, m, d] = ymd(u);
  if (gran === 'Mes') {
    if (u >= Date.UTC(y, m, 0) / DIA) return null;
    const ini = Date.UTC(y, m - 1, 1) / DIA, refIni = Date.UTC(y, m - 2, 1) / DIA;
    const refFin = Math.min(refIni + d - 1, ini - 1);
    return { ini, fin: u, refIni, refFin, rot: `${MES[m - 1]} 1–${d}`, rotRef: `1–${ymd(refFin)[2]} ${MES[ymd(refIni)[1] - 1]}` };
  }
  if (gran === 'Semana') {
    const wd = diaSemana(u);
    if (wd === 6) return null;
    return { ini: u - wd, fin: u, refIni: u - wd - 7, refFin: u - 7, rot: `hasta el ${d} ${MES[m - 1]}`,
      rotRef: 'los mismos días de la semana anterior' };
  }
  if (gran === 'Año') {
    if (m === 12 && d === 31) return null;
    const refFin = Math.min(Date.UTC(y - 1, m - 1, d) / DIA, Date.UTC(y - 1, m, 0) / DIA);
    return { ini: Date.UTC(y, 0, 1) / DIA, fin: u, refIni: Date.UTC(y - 1, 0, 1) / DIA, refFin,
      rot: `${y} al ${d} ${MES[m - 1]}`, rotRef: `${y - 1} al ${ymd(refFin)[2]} ${MES[ymd(refFin)[1] - 1]}` };
  }
  return null;
}
function etq(k, gran, largo, F) {
  if (gran === 'Mes') { const [y, m] = k.split('-').map(Number); return largo ? `${MES[m - 1]} ${y}` : `${MES[m - 1]} ${String(y).slice(2)}`; }
  if (gran === 'Semana') { const n = dn(k); return largo ? `sem. del ${fCorta(n)}` : fCorta(n); }
  if (gran === 'Documento') {
    const [f, doc, prov] = k.split('|');
    const c = fCorta(dn(f));
    if (!largo) return c;
    return [c, F.provs[+prov], doc.startsWith('#') ? '' : F.docs[+doc]].filter(Boolean).join(' · ');
  }
  return k;
}

// producto._serie: `h` son las líneas del producto (de la más vieja a la
// más nueva). Devuelve null sin compras en la ventana.
function serie(h, gran, op, ultimo, rango) {
  if (!h.length) return null;
  let [ini, fin] = ventana(op, ultimo, h[0].d, rango);
  if (gran !== 'Documento') ini = inicioDe(ini, gran);
  const w = h.filter((l) => l.d >= ini && l.d <= fin);
  if (!w.length) return null;
  let keys;
  if (gran === 'Documento') {
    const pad = (x) => String(x).padStart(6, '0');
    w.forEach((l) => { l.k = `${iso(l.d)}|${l.sinDoc ? '#' + l.n : pad(l.doc)}|${pad(l.prov)}`; });
    keys = [...new Set(w.map((l) => l.k))].sort();
  } else {
    w.forEach((l) => { l.k = clave(l.d, gran); });
    keys = secuencia(ini, fin, gran);
  }
  const agg = new Map(keys.map((k) => [k, { c: 0, v: 0, pc: 0, pv: 0, rc: 0, cr: 0, fl: 0, docs: 0 }]));
  w.forEach((l) => {
    const a = agg.get(l.k);
    if (!a) return;
    const ok = !l.flag && l.cant > 0, okr = ok && finito(l.ref);
    a.c += l.cant; a.v += l.valor; a.docs += 1;
    if (l.flag) a.fl += 1;
    if (ok) { a.pc += l.cant; a.pv += l.valor; }
    if (okr) { a.rc += l.ref * l.cant; a.cr += l.cant; }
  });
  let parc = gran !== 'Documento' ? parcial(gran, ultimo) : null;
  if (parc && clave(parc.ini, gran) !== keys[keys.length - 1]) parc = null;
  let refq = null;
  if (parc) refq = h.filter((l) => l.d >= parc.refIni && l.d <= parc.refFin).reduce((s, l) => s + l.cant, 0);
  return { keys, agg: keys.map((k) => agg.get(k)), lineas: w, parc, refq, ini, fin };
}
// producto._precios: sin las líneas marcadas.
const precioDe = (a) => (a.pc > 0 ? a.pv / a.pc : null);
const habDe = (a) => (a.cr > 0 ? a.rc / a.cr : null);

// ── Los datos ────────────────────────────────────────────────────────────
function leerFicha(data) {
  const base = dn(data.base);
  const L = data.lineas.map((ls) => ls.map((l, n) => ({
    d: base + l[RL.dia], prov: l[RL.prov], doc: l[RL.doc], cant: l[RL.cant] || 0, valor: l[RL.valor] || 0,
    ref: l[RL.ref], flag: FLAGS[l[RL.flag]] || '', sinDoc: !data.docs[l[RL.doc]], n })));
  return { sello: data.sello, nombres: data.nombres, cods: data.cods || [], um: data.um, provs: data.provs, docs: data.docs, L,
    porDoc: null };
}
function leerRank(data) {
  const grupo = (r, o) => ({ valor: r[o] || 0, prev: r[o + 1] || 0, var: r[o + 2], est: r[o + 3], hab: r[o + 4], n: r[o + 5],
    nflag: r[o + 6], vref: r[o + 7] || 0, refc: r[o + 8] || 0 });
  return {
    sello: data.sello, R0: dn(data.rango[0]), R1: dn(data.rango[1]), ULT: dn(data.ultimo), DIAS: data.dias,
    n80: data.n80, nflag: data.nflag, prevTotal: data.prev_total, nomf: data.nomf, noms: data.noms,
    P: data.prods.map((r) => ({ i: r[RP.i], fam: r[RP.fam], sub: r[RP.sub], um: r[RP.um], valor: r[RP.valor] || 0,
      cant: r[RP.cant] || 0, var: r[RP.var], est: r[RP.est], pp: r[RP.pp], hab: r[RP.hab], ppv: r[RP.ppv],
      nflag: r[RP.nflag], docs: r[RP.docs], ult: r[RP.ult] ? dn(r[RP.ult]) : null, ultp: r[RP.ultp], cada: r[RP.cada],
      prev: r[RP.prev] || 0, vref: r[RP.vref], refc: r[RP.refc] })),
    FAMS: data.fams.map((r) => ({ fam: r[0], ...grupo(r, 1) })),
    SUBS: data.subs.map((r) => ({ fam: r[0], sub: r[1], ...grupo(r, 2) })),
    // Sin compras en el rango y con compras en el período anterior (regla #774).
    DEJ: (data.dejados || []).map((r) => ({ i: r[0], fam: r[1], sub: r[2], um: r[3], prev: r[4] || 0, n90: r[5], ult: r[6] ? dn(r[6]) : null, ultp: r[7], cada: r[8],
      valor: 0, cant: 0, var: -100, est: '', pp: null, hab: null, ppv: null, nflag: 0, docs: 0, vref: 0, refc: 0, dej: true })),
    pagina: data.pagina || null,
  };
}
// Las líneas de un comprobante, de todos los productos (se arma una vez).
function porDoc(F) {
  if (!F.porDoc) {
    F.porDoc = new Map();
    F.L.forEach((ls, i) => ls.forEach((l) => {
      if (l.sinDoc) return;
      const k = `${l.doc}|${l.d}|${l.prov}`;
      if (!F.porDoc.has(k)) F.porDoc.set(k, []);
      F.porDoc.get(k).push({ ...l, prod: i });
    }));
  }
  return F.porDoc;
}

const G = window.__cpProd || (window.__cpProd = { st: { kpi: 'todos', ver: 'todos', hasta: '1', ab: {}, q: '', sub: null, foco: null, amp: null, menu: null, tab: 'curva', gran: 'Mes', op: '3m', pw: '90', per: null, cprov: null, doc: null }, R: null, F: null });
if (G.st.det == null) G.st.det = !!lfLeer('cp_prod_det', false);
if (!G.st.pleg) G.st.pleg = lfLeer('cp_prod_pleg', {});

// ── La ficha ─────────────────────────────────────────────────────────────
function porDocumento(Ls) {
  const g = new Map();
  Ls.forEach((l) => {
    const k = `${l.d}|${l.doc}|${l.prov}`;
    const a = g.get(k) || { d: l.d, doc: l.doc, prov: l.prov, sinDoc: l.sinDoc, cant: 0, valor: 0, refs: [], flag: '' };
    a.cant += l.cant; a.valor += l.valor;
    if (finito(l.ref)) a.refs.push(l.ref);
    if (l.flag > a.flag) a.flag = l.flag;
    g.set(k, a);
  });
  return [...g.values()].map((a) => ({ ...a, ref: a.refs.length ? a.refs.reduce((s, x) => s + x, 0) / a.refs.length : null }));
}
function ayudaMarca(a, um) {
  if (a.flag === 'um') {
    const b = a.cant / 0.75;
    return `${cant(a.cant, um)}: una unidad que se cuenta entera viene con decimales.`
      + (Math.abs(b - Math.round(b)) < 0.01 ? ` ${Math.round(b)} botellas × 0,75 L = ${cant(a.cant)}: ¿se cargó en litros?` : ' ¿Se cargó en otra unidad?');
  }
  if (a.flag === 'precio' && a.cant && a.ref) {
    const pu = a.valor / a.cant;
    return `Precio ${precio(pu)} contra un habitual de ${precio(a.ref)} (${(pu / a.ref).toFixed(1)} veces): ¿error de tipeo, de unidad o de producto?`;
  }
  return '';
}
const celda = (t, cls, ayuda) => `<span class="${cls || ''}"${ayuda ? ` title="${esc(ayuda)}"` : ''}>${t}</span>`;
function tabla(tipo, cab, filas, tot) {
  return `<div class="ft ${tipo}"><div class="ft-f ft-h">${cab.join('')}</div><div class="ft-l">${filas.join('')}</div>`
    + `<div class="ft-f ft-t">${tot.join('')}</div></div>`;
}
function tablaProveedores(Ls, um) {
  if (!Ls.length) return { n: 0, html: '<div class="nota-v">Sin compras en esos días.</div>' };
  const { F } = G;
  const g = new Map();
  Ls.forEach((l) => {
    const a = g.get(l.prov) || { prov: l.prov, c: 0, v: 0, pc: 0, pv: 0, ult: 0, fl: 0 };
    a.c += l.cant; a.v += l.valor;
    if (!l.flag && l.cant > 0) { a.pc += l.cant; a.pv += l.valor; }
    a.ult = Math.max(a.ult, l.d);
    if (l.flag) a.fl += 1;
    g.set(l.prov, a);
  });
  const rows = [...g.values()].sort((a, b) => b.v - a.v);
  rows.forEach((a) => { a.p = a.pc > 0 ? a.pv / a.pc : (a.c > 0 ? a.v / a.c : null); });
  const ps = rows.map((a) => a.p).filter(finito), min = ps.length ? Math.min(...ps) : null;
  const tot = rows.reduce((s, a) => s + a.v, 0) || 1;
  const filas = rows.map((a) => {
    let dif;
    if (rows.length > 1 && min != null && a.p === min) dif = celda('<i class="chip barato">el más bajo</i>', 'r');
    else if (rows.length > 1 && finito(a.p) && min) { const x = (a.p / min - 1) * 100; dif = celda(`+${x.toFixed(1)} %`, 'r igual'); }
    else dif = celda('—', 'r igual');
    return `<div class="ft-f" data-acc="prov" data-v="${a.prov}" title="Clic: sus compras">`
      + celda(esc(F.provs[a.prov]) + (a.fl ? ' <i class="w" title="Incluye una compra para revisar">⚠</i>' : ''), 'nm', F.provs[a.prov])
      + celda(cant(a.c, um), 'r') + celda(precio(a.p), 'r') + dif + celda(soles(a.v), 'r')
      + celda(`${Math.round(a.v / tot * 100)}%`, 'r gr') + celda(fCorta(a.ult), 'r gr') + '</div>';
  });
  const pc = rows.reduce((s, a) => s + a.pc, 0), pv = rows.reduce((s, a) => s + a.pv, 0);
  const c = rows.reduce((s, a) => s + a.c, 0), v = rows.reduce((s, a) => s + a.v, 0);
  return { n: rows.length, html: tabla('pv',
    [celda('Proveedor'), celda('Cant.', 'r'), celda('Precio', 'r'), celda('Vs. más barato', 'r', 'Cuánto más caro sale que el más barato, en los mismos días'),
      celda('Valor', 'r'), celda('%', 'r'), celda('Última', 'r')],
    filas,
    [celda(`Total · ${rows.length} ${rows.length === 1 ? 'proveedor' : 'proveedores'}`, 'nm'), celda(cant(c, um), 'r'),
      celda(precio(pc ? pv / pc : (c ? v / c : null)), 'r'), celda(''), celda(soles(v), 'r'), celda('100%', 'r'), celda('')]) };
}
function tablaCompras(Ls, um) {
  const { F } = G;
  const D = porDocumento(Ls).sort((a, b) => b.d - a.d);
  if (!D.length) return { n: 0, html: '<div class="nota-v">Sin compras en este ámbito.</div>' };
  const ok = D.filter((a) => !a.flag && a.cant > 0);
  const pc = ok.reduce((s, a) => s + a.cant, 0), pv = ok.reduce((s, a) => s + a.valor, 0);
  const okr = ok.filter((a) => finito(a.ref));
  const rc = okr.reduce((s, a) => s + a.ref * a.cant, 0), cr = okr.reduce((s, a) => s + a.cant, 0);
  const ph = pc && rc && cr ? (pv / pc) / (rc / cr) * 100 - 100 : null;
  const filas = D.map((a) => {
    const pu = a.cant ? a.valor / a.cant : null;
    const h = pu && finito(a.ref) && a.ref > 0 ? (pu / a.ref - 1) * 100 : null;
    const k = `${a.doc}|${a.d}|${a.prov}`, ab = !a.sinDoc && G.st.doc === k;
    const acc = a.sinDoc ? '' : ` data-acc="doc" data-v="${k}" title="Clic: el comprobante entero"`;
    return `<div class="ft-f${ab ? ' foco' : ''}"${acc}>` + celda(fCorta(a.d)) + celda(esc(F.provs[a.prov]), 'nm', F.provs[a.prov])
      + celda(esc(F.docs[a.doc] || '—'), 'nm gr') + celda(cant(a.cant), 'r') + celda(precio(pu), `r${a.flag ? ' nar' : ''}`)
      + (a.flag ? celda('<i class="chip revisar">revisar</i>', 'r', ayudaMarca(a, um)) : celda(fmtVar(h), `r b ${clsVar(h)}`)) + celda(soles(a.valor), 'r') + '</div>'
      + (ab ? comprobante(k) : '');
  });
  return { n: D.length, html: tabla('cp',
    [celda('Fecha'), celda('Proveedor'), celda('Documento'), celda('Cant.', 'r'), celda('Precio', 'r'),
      celda('Vs. hab.', 'r', 'El precio de esa compra contra el habitual de ese día'), celda('Valor', 'r')],
    filas,
    [celda(`Total · ${D.length} ${D.length === 1 ? 'compra' : 'compras'}`, 'nm tot3'), celda(cant(D.reduce((s, a) => s + a.cant, 0), um), 'r'),
      celda(precio(pc ? pv / pc : null) + (D.some((a) => a.flag) ? ' <i class="w" title="Sin las compras marcadas para revisar">⚠</i>' : ''), 'r'),
      celda(fmtVar(ph), `r ${clsVar(ph)}`), celda(soles(D.reduce((s, a) => s + a.valor, 0)), 'r')]) };
}
function tablaPeriodos(S, gran, um, sel) {
  const { F } = G;
  const tot = S.agg.reduce((s, a) => s + a.v, 0) || 1;
  const n = S.keys.length;
  let prev = null;
  const filas = S.keys.map((k, i) => {
    const a = S.agg[i], p = precioDe(a), h = habDe(a);
    const hv = finito(p) && finito(h) && h ? (p / h - 1) * 100 : null;
    const dp = finito(p) ? varPct(p, prev) : null;
    if (finito(p)) prev = p;
    const parc = S.parc && i === n - 1;
    const lab = etq(k, gran, true, F) + (parc ? (gran === 'Mes' ? ` (1–${ymd(S.parc.fin)[2]})` : ' (en curso)') : '');
    return `<div class="ft-f${k === sel ? ' foco' : ''}" data-acc="per" data-v="${esc(k)}" title="Clic: sus compras">`
      + celda(esc(lab), `nm${parc ? ' parc' : ''}`) + celda(a.c ? cant(a.c, um) : '—', 'r')
      + celda(precio(p) + (a.fl ? ' <i class="w" title="Precio sin las compras marcadas para revisar">⚠</i>' : ''), 'r')
      + celda(fmtVar(hv), `r b ${clsVar(hv)}`) + celda(a.v ? soles(a.v) : '—', 'r')
      + celda(a.v ? `${Math.round(a.v / tot * 100)}%` : '—', 'r gr') + celda(String(a.docs || '—'), 'r')
      + celda(fmtVar(dp), `r b ${clsVar(dp)}`) + '</div>';
  });
  const pc = S.agg.reduce((s, a) => s + a.pc, 0), pv = S.agg.reduce((s, a) => s + a.pv, 0);
  const rc = S.agg.reduce((s, a) => s + a.rc, 0), cr = S.agg.reduce((s, a) => s + a.cr, 0);
  const ph = pc && rc && cr ? (pv / pc) / (rc / cr) * 100 - 100 : null;
  return tabla('pe',
    [celda('Período'), celda('Cant.', 'r'), celda('Precio', 'r'), celda('Vs. hab.', 'r'), celda('Valor', 'r'),
      celda('%', 'r', '% del valor de la curva'), celda('Docs', 'r'), celda('Δ precio', 'r', 'El precio contra el período anterior')],
    filas,
    [celda('Total', 'nm'), celda(cant(S.agg.reduce((s, a) => s + a.c, 0), um), 'r'), celda(precio(pc ? pv / pc : null), 'r'),
      celda(fmtVar(ph), `r ${clsVar(ph)}`), celda(soles(tot), 'r'), celda('100%', 'r'), celda(String(S.agg.reduce((s, a) => s + a.docs, 0)), 'r'), celda('')]);
}

// ── La lista ─────────────────────────────────────────────────────────────
const nomF = (R, f) => R.nomf[f] || f;
const nomS = (R, s) => R.noms[s] || s;

// Lo que dicen los indicadores y la lista con el estado de hoy. Pura: la corre el test.
function vista(R, F, st) {
  const q = st.q || '', okS = (p) => !st.sub || (p.fam === st.sub[0] && p.sub === st.sub[1]);
  const ok = (p) => okS(p) && (!q || coincide(`${F.nombres[p.i]} ${F.cods[p.i] || ''}`, q));
  const base = R.P.filter(ok), dej = R.DEJ.filter(ok).sort((a, b) => b.prev - a.prev);
  const vT = base.reduce((s, p) => s + p.valor, 0) || 1, prevT = base.reduce((s, p) => s + p.prev, 0) + dej.reduce((s, p) => s + p.prev, 0);
  const en80 = new Set(); let ac = 0;
  [...base].sort((a, b) => b.valor - a.valor).forEach((p) => { if (ac / vT < 0.8) en80.add(p.i); ac += p.valor; });
  const nv = base.filter((p) => p.est), rev = base.filter((p) => p.nflag > 0), seg = dej.filter((p) => p.n90 >= 3), nu = nv.filter((p) => p.est === 'nuevo');
  let vis = st.kpi === 'nv' ? nv : st.kpi === 'dej' ? dej : st.kpi === 'rev' ? rev : base;
  if (st.ver === 'n80') vis = vis.filter((p) => en80.has(p.i) || p.dej);
  const s = st.sort;
  const k = s ? { nom: (p) => sinTildes(F.nombres[p.i]), val: (p) => p.valor, ant: (p) => p.valor - p.prev, hab: (p) => (finito(p.hab) ? p.hab : -1e16) }[s.col] : null;
  vis = [...vis].sort(k ? (a, b) => { const x = k(a), y = k(b); return (x < y ? -1 : x > y ? 1 : 0) * s.dir; } : st.kpi === 'dej' ? (a, b) => b.prev - a.prev : (a, b) => b.valor - a.valor);
  // De dónde sale la diferencia contra el período anterior: las cuatro partes suman el total.
  const mas = base.filter((p) => !p.est && p.valor > p.prev), men = base.filter((p) => !p.est && p.valor < p.prev);
  const dif = { mas: mas.reduce((s2, p) => s2 + p.valor - p.prev, 0), nMas: mas.length, men: men.reduce((s2, p) => s2 + p.valor - p.prev, 0), nMen: men.length,
    nv: nv.reduce((s2, p) => s2 + p.valor, 0), nNv: nv.length, dej: -dej.reduce((s2, p) => s2 + p.prev, 0), nDej: dej.length, total: base.reduce((s2, p) => s2 + p.valor, 0) - prevT };
  return { base, dej, vT, prevT, en80, nv, rev, seg, nu, vis, dif };
}

function kpisHtml(V, R, F) {
  const st = G.st, kp = (id, rot, val, d, tip, vc) => `<button class="lf-kpi${st.kpi === id ? ' on' : ''}" data-acc="kpi" data-v="${id}" aria-pressed="${st.kpi === id}" title="${esc(tip)}"><span class="r">${esc(rot)}</span><span class="v ${vc}">${esc(val)}</span><span class="d">${esc(d)}</span></button>`;
  const ant = tramo(R.R0 - R.DIAS, R.R0 - 1);
  const fl = V.rev.flatMap((p) => F.L[p.i].filter((l) => l.d >= R.R0 && l.d <= R.R1 && l.flag));
  const vFl = fl.reduce((s, l) => s + l.valor, 0), sumV = V.nv.reduce((s, p) => s + p.valor, 0), sumD = V.dej.reduce((s, p) => s + p.prev, 0);
  return kp('todos', 'Productos', ent(V.base.length), `${soles(V.vT)} · ${fmtVar(varPct(V.vT, V.prevT))} · ${V.en80.size} hacen el 80 %`, `Lo comprado en el rango, sin IGV, contra ${ant}.`, '')
    + kp('nv', 'Nuevos o vuelven', ent(V.nv.length), `${solesG(sumV)} · ${V.nu.length} por primera vez`, 'Sin compras en el período anterior.', '')
    + kp('dej', 'Se dejaron de comprar', ent(V.dej.length), `${solesG(-sumD)} · ${V.seg.length} se compraban seguido`, 'Se compraron en el período anterior y en este no. «Seguido»: 3 compras o más en los 90 días anteriores.', '')
    + kp('rev', 'Para revisar', ent(V.rev.length), `${fl.length} ${fl.length === 1 ? 'compra' : 'compras'} · ${soles(vFl)} · fuera de los precios`, 'Una compra de S/ 50 o más a 2,5 veces su habitual o a menos de 0,4, o con decimales en una unidad entera.', V.rev.length ? 'nar' : '');
}

// La mini-curva de 13 meses de un producto: el precio ponderado de cada mes, sin marcadas.
function spark(i) {
  const cache = G.spark || (G.spark = new Map());
  if (cache.has(i)) return cache.get(i);
  const { R, F } = G;
  const ini = restarMeses(R.ULT, 12) + 1, keys = secuencia(inicioDe(ini, 'Mes'), R.ULT, 'Mes');
  const ag = new Map(keys.map((k) => [k, { pc: 0, pv: 0 }]));
  F.L[i].forEach((l) => {
    if (l.d < inicioDe(ini, 'Mes') || l.flag || l.cant <= 0) return;
    const a = ag.get(clave(l.d, 'Mes'));
    if (a) { a.pc += l.cant; a.pv += l.valor; }
  });
  const pts = lfSpark(keys.map((k) => { const a = ag.get(k); return a.pc > 0 ? a.pv / a.pc : null; }));
  cache.set(i, pts);
  return pts;
}

function listaHtml(V) {
  const { R, F, st } = G, s = st.sort, amp = !!st.det, arbol = st.ver === 'fam';
  const th = (k, t, ayuda, cls) => `<th class="${cls}"${ayuda ? ` title="${esc(ayuda)}"` : ''}><button data-acc="orden" data-v="${k}">${esc(t)}${s && s.col === k ? (s.dir > 0 ? ' ↑' : ' ↓') : ''}</button></th>`;
  const vMax = Math.max(1, ...V.vis.map((p) => p.valor));
  const filaPd = (p, pad) => {
    const nom = F.nombres[p.i];
    const ayudaAnt = p.est === 'nuevo' ? 'Primera compra' : p.est === 'vuelve' ? 'No se compró en el período anterior' : p.dej ? `Última compra: ${p.ult != null ? fCorta(p.ult) : '—'}` : `${soles(p.prev)} → ${soles(p.valor)} · ${fmtVar(p.var)}`;
    return `<tr class="${p.i === st.foco ? 'on' : ''}" data-acc="fila" data-v="${p.i}"><td class="l nm" style="padding-left:${8 + pad}px" title="${esc(nom)}${F.cods[p.i] ? ` · cód. ${esc(F.cods[p.i])}` : ''}${p.nflag ? ' · tiene una compra para revisar' : ''}">${p.nflag ? '<i class="w">⚠</i> ' : ''}${esc(nom)}${!amp && F.cods[p.i] ? `<span class="lf-cod">${esc(F.cods[p.i])}</span>` : ''}${p.dej ? `<span class="lf-chip">${p.n90} en 90 d</span>` : ''}</td>`
      + (amp ? `<td class="gris">${esc(F.cods[p.i] || '—')}</td>` : '')
      + `<td class="bv" style="--b:${(p.valor / vMax * 100).toFixed(1)}%">${soles(p.valor)}</td>${amp ? `<td class="gris">${p.valor ? `${(p.valor / V.vT * 100).toFixed(1)} %` : '—'}</td>` : ''}`
      + `<td class="${p.est ? 'mar' : 'gris'}" title="${esc(ayudaAnt)}">${esc(p.est || solesG(p.valor - p.prev))}</td><td class="${colorPrecio(p.hab)}">${fmtVar(p.hab)}</td>`
      + (amp ? `<td>${p.dej ? '—' : cant(p.cant, p.um)}</td><td>${precio(p.pp)}</td><td class="${colorPpv(p.ppv)}">${finito(p.ppv) && !p.dej ? solesG(p.ppv) : '—'}</td><td class="gris">${p.docs || '—'}</td><td class="gris">${provsDe(p) || '—'}</td><td class="gris">${p.ult != null ? fCorta(p.ult) : '—'}</td>`
        + `<td class="t"><svg viewBox="0 0 68 20" aria-hidden="true"><polyline points="${spark(p.i)}"></polyline></svg></td>` : '') + '</tr>';
  };
  const grupo = (id, nom, xs, pad, cls, niv) => {
    const ab = abierto(id, niv), v = xs.reduce((a, p) => a + p.valor, 0), pr = xs.reduce((a, p) => a + p.prev, 0), vr = xs.reduce((a, p) => a + p.vref, 0), rc = xs.reduce((a, p) => a + p.refc, 0), hab = rc > 0 ? (vr / rc - 1) * 100 : null;
    return `<tr class="${cls}" data-acc="grupo" data-v="${esc(id)}" data-n="${niv}"><td class="l" style="padding-left:${8 + pad}px" title="${esc(nom)}">${ab ? '▾' : '▸'} ${esc(nom)}</td>${amp ? '<td></td>' : ''}<td class="bv" style="--b:${(v / V.vT * 100).toFixed(1)}%">${soles(v)}</td>${amp ? `<td class="gris">${(v / V.vT * 100).toFixed(1)} %</td>` : ''}<td class="gris">${solesG(v - pr)}</td><td class="${colorPrecio(hab)}">${fmtVar(hab)}</td>`
      + (amp ? `<td></td><td></td><td class="${colorPpv(vr - rc)}">${solesG(vr - rc)}</td><td></td><td></td><td></td><td class="t"></td>` : '') + '</tr>';
  };
  const abierto = (id, niv) => (st.ab[id] != null ? st.ab[id] : niv < +st.hasta);
  let cuerpo;
  if (arbol) {
    // En «Vs. antes» cuentan también los que se dejaron de comprar, o no suma el total.
    const src = st.kpi === 'todos' ? [...V.vis, ...V.dej] : V.vis, porF = new Map();
    src.forEach((p) => { if (!porF.has(p.fam)) porF.set(p.fam, []); porF.get(p.fam).push(p); });
    cuerpo = [...porF].sort((a, b) => b[1].reduce((s2, p) => s2 + p.valor, 0) - a[1].reduce((s2, p) => s2 + p.valor, 0)).map(([f, xs]) => {
      const idF = `f|${f}`; let h = grupo(idF, nomF(R, f), xs, 0, 'g0', 0);
      if (!abierto(idF, 0)) return h;
      const porS = new Map();
      xs.forEach((p) => { if (!porS.has(p.sub)) porS.set(p.sub, []); porS.get(p.sub).push(p); });
      [...porS].sort((a, b) => b[1].reduce((s2, p) => s2 + p.valor, 0) - a[1].reduce((s2, p) => s2 + p.valor, 0)).forEach(([s2, ys]) => {
        const idS = `s|${f}|${s2}`; h += grupo(idS, nomS(R, s2), ys, 12, '', 1);
        if (abierto(idS, 1)) h += ys.filter((p) => !p.dej || st.kpi === 'dej').map((p) => filaPd(p, 26)).join('');
      });
      return h;
    }).join('');
  } else cuerpo = V.vis.map((p) => filaPd(p, 0)).join('');
  const tods = st.kpi === 'todos' && st.ver !== 'n80';
  const tv = V.vis.reduce((a, p) => a + p.valor, 0), tp = tods ? V.prevT : V.vis.reduce((a, p) => a + p.prev, 0), vr = V.vis.reduce((a, p) => a + (p.vref || 0), 0), rc = V.vis.reduce((a, p) => a + (p.refc || 0), 0), th2 = rc > 0 ? (vr / rc - 1) * 100 : null;
  const ayT = tods && V.dej.length ? `Con los ${V.dej.length} productos que se dejaron de comprar: ${soles(V.dej.reduce((a, p) => a + p.prev, 0))}` : '';
  return `<div class="lf-scroll" data-tabla="lista"><table class="lf-t"><thead><tr>${th('nom', 'Producto', '', 'l')}${amp ? '<th class="w-pr">Código</th>' : ''}${th('val', 'Compra', '', 'w-im')}${amp ? th('val', '%', '% sobre lo comprado', 'w-pc') : ''}`
    + `${th('ant', 'Vs. antes', 'Contra el período anterior de igual largo. En soles y en gris: comprar más o menos no es bueno ni malo.', 'w-im')}${th('hab', 'Vs. hab.', 'El precio contra el habitual: la mediana de los 90 días anteriores, sin las compras para revisar', 'w-h')}`
    + (amp ? '<th class="w-x">Cantidad</th><th class="w-pr">Precio</th><th class="w-pr" title="(Precio pagado − habitual) × cantidad">Efecto</th><th class="w-n">Compras</th><th class="w-n">Provs.</th><th class="w-pr">Última</th><th class="w-t" title="El precio ponderado de cada mes">13 meses</th>' : '')
    + '</tr></thead><tbody>'
    + `<tr class="tot"><td class="l">Total · ${ent(V.vis.length)} productos</td>${amp ? '<td></td>' : ''}<td>${soles(tv)}</td>${amp ? `<td>${Math.round(tv / V.vT * 100)} %</td>` : ''}<td title="${esc(ayT)}">${solesG(tv - tp)}</td><td class="${colorPrecio(th2)}">${fmtVar(th2)}</td>${amp ? `<td></td><td></td><td class="${colorPpv(vr - rc)}">${solesG(vr - rc)}</td><td></td><td></td><td></td><td></td>` : ''}</tr>`
    + (cuerpo || `<tr><td colspan="${amp ? 14 : 4}" class="lf-vacio">Nada con ese filtro.</td></tr>`)
    + `</tbody></table></div><div class="lf-pie"><p class="lf-nota">${ent(V.vis.length)} productos · sin IGV · contra ${esc(tramo(R.R0 - R.DIAS, R.R0 - 1))}${V.rev.length ? ' · ⚠ con una compra para revisar' : ''}</p>${lfAmp('izq', st.amp === 'izq', 'la lista')}</div>`;
}
function provsDe(p) {
  const { F, R } = G;
  return new Set(F.L[p.i].filter((l) => l.d >= R.R0 && l.d <= R.R1).map((l) => l.prov)).size;
}

function comoHtml(R) {
  const ant = tramo(R.R0 - R.DIAS, R.R0 - 1);
  return `<p>Lo comprado del ${fCorta(R.R0)} al ${fCorta(R.R1)}, sin IGV, contra los mismos ${R.DIAS} días anteriores (${esc(ant)}).</p><dl>`
    + '<dt>Productos</dt><dd>Los comprados en el rango; «hacen el 80 %», los que suman el 80 % de lo comprado.</dd>'
    + '<dt>Nuevos o vuelven</dt><dd>Sin compras en el período anterior; «por primera vez», sin ninguna antes.</dd>'
    + '<dt>Se dejaron</dt><dd>Comprados en el período anterior y no en este. «Seguido»: 3 compras o más en los 90 días anteriores.</dd>'
    + '<dt>Para revisar</dt><dd>Una compra de S/ 50 o más a 2,5 veces su habitual o a menos de 0,4, o con decimales en una unidad entera. No entra en ningún precio; sí en la cantidad y el valor.</dd>'
    + '<dt>Vs. antes</dt><dd>En soles y en gris: comprar más o menos no es bueno ni malo.</dd>'
    + '<dt>Vs. hab.</dt><dd>El precio ponderado (soles ÷ cantidad) contra el habitual: la mediana de los 90 días anteriores a cada compra. En rojo si subió, en verde si bajó.</dd>'
    + '<dt>Efecto</dt><dd>(Precio pagado − habitual) × cantidad. Con «Detalle».</dd></dl><p>Es un cálculo propio, no un estándar.</p>';
}

function excel() {
  const { R, F } = G, V = G.V;
  const filas = V.vis.map((f) => [F.nombres[f.i], nomF(R, f.fam), nomS(R, f.sub), f.um, f.valor, f.cant, f.valor / V.vT * 100, f.prev, f.var, f.est || (f.dej ? 'dejado' : ''), f.pp, f.hab, f.ppv, f.docs, f.nflag]);
  bajar(`compras_productos_${iso(R.R0)}_${iso(R.R1)}.xlsx`, libro([{ nombre: 'Productos', cabeza: ['Producto', 'Familia', 'Subfamilia', 'Unidad', 'Valor (S/)', 'Cantidad', '% de lo comprado', 'Período anterior (S/)', 'Δ % vs. período anterior',
    'Estado', 'Precio ponderado (S/)', 'vs. precio habitual %', 'Impacto del precio (S/)', 'Compras', 'Líneas para revisar'], filas }]));
}

// Sin nada elegido, el panel responde la pregunta de la vista.
function resumenHtml(V) {
  const { R, F, st } = G, ant = tramo(R.R0 - R.DIAS, R.R0 - 1);
  const item = (n, s, v, c, acc, val, on) => `<button class="lf-fi${on ? ' on' : ''}" data-acc="${acc}" data-v="${esc(val)}"><span class="n" title="${esc(n)}">${esc(n)}</span><small title="${esc(s)}">${esc(s)}</small><b class="${c}">${esc(v)}</b></button>`;
  const miga = `${st.sub ? nomS(R, st.sub[1]) : 'Todo lo comprado'} · ${fCorta(R.R0)} – ${fCorta(R.R1)}`;
  const cab = (t) => `<div class="lf-fcab"><div class="lf-ftit"><span class="lf-miga">${esc(miga)}</span><h3>${esc(t)}</h3></div>${lfAmp('panel', st.amp === 'panel', 'el resumen')}</div>`;
  const pleg = (id, t, c, crece) => { const ab = st.pleg[id] !== false; return lfPleg(id, t, c, ab).replace('lf-pleg', `lf-pleg${crece && ab ? ' crece' : ''}`); };
  const lista = (t, xs) => pleg(t, esc(t), `<div class="lf-lista">${xs}</div>`, true);
  if (st.kpi === 'nv') {
    return cab('Lo que apareció') + `<p class="lf-frase">${esc(`${V.nv.length} productos no se compraron en ${ant}: ${V.nu.length} por primera vez y ${V.nv.length - V.nu.length} que vuelven. Suman ${soles(V.nv.reduce((a, p) => a + p.valor, 0))}.`)}</p>`
      + lista('Los que más pesan', [...V.nv].sort((a, b) => b.valor - a.valor).slice(0, 40).map((p) => item(F.nombres[p.i], p.est, soles(p.valor), '', 'fila', p.i)).join(''));
  }
  if (st.kpi === 'dej') {
    return cab('Lo que se dejó de comprar') + `<p class="lf-frase">${esc(`${V.dej.length} productos que se compraron en ${ant} no se compraron ahora: ${soles(V.dej.reduce((a, p) => a + p.prev, 0))}. ${V.seg.length} se compraban seguido (${soles(V.seg.reduce((a, p) => a + p.prev, 0))}). Puede ser la carta, la temporada o que hay stock: la app sólo ve que no se compró.`)}</p>`
      + lista('Los que más pesaban', V.dej.slice(0, 40).map((p) => item(F.nombres[p.i], `${p.n90} ${p.n90 === 1 ? 'compra' : 'compras'} en 90 d`, soles(p.prev), '', 'fila', p.i)).join(''));
  }
  if (st.kpi === 'rev') {
    return cab('Compras para revisar') + '<p class="lf-frase">Cada uno tiene una compra muy lejos de su habitual, o con decimales en una unidad que se cuenta entera. Suelen ser errores de tipeo o de unidad: no entran en ningún precio, pero sí en la cantidad y el valor.</p>'
      + lista('Los productos', [...V.rev].sort((a, b) => b.valor - a.valor).map((p) => item(F.nombres[p.i], `${p.nflag} ${p.nflag === 1 ? 'línea' : 'líneas'}`, soles(p.valor), '', 'fila', p.i)).join(''));
  }
  const d = V.dif, T = d.total, porS = new Map();
  V.base.forEach((p) => { const k = `${p.fam}\u001f${p.sub}`; porS.set(k, (porS.get(k) || 0) + p.valor); });
  const fila = (n, v, cls) => `<span class="${cls || ''}">${esc(n)}</span><b class="${cls || ''}">${esc(v)}</b>`;
  return cab('En qué se va') + `<p class="lf-frase">${esc(`${V.en80.size} de ${ent(V.base.length)} productos hacen el 80 % de lo comprado. Compraste ${soles(Math.abs(T))} ${T < 0 ? 'menos' : 'más'} que en ${ant} (${fmtVar(varPct(V.vT, V.prevT))}).`)}</p>`
    + pleg('dif', 'De dónde sale la diferencia', `<div class="lf-dif">${fila(`Los mismos, se compró más · ${d.nMas}`, solesG(d.mas))}${fila(`Los mismos, se compró menos · ${d.nMen}`, solesG(d.men))}${fila(`Nuevos o vuelven · ${d.nNv}`, solesG(d.nv))}${fila(`Se dejaron de comprar · ${d.nDej}`, solesG(d.dej))}${fila('Total', solesG(T), 'tt')}</div>`)
    + lista('Por subfamilia', [...porS].sort((a, b) => b[1] - a[1]).map(([k, v]) => { const [f, s2] = k.split('\u001f'); return item(nomS(R, s2), `${(v / V.vT * 100).toFixed(1)} %`, soles(v), '', 'sub', k, st.sub && st.sub[0] === f && st.sub[1] === s2); }).join(''))
    + lfFuera(R.pagina, soles, esc);
}

// El comprobante entero de una compra: sus líneas de TODOS los productos.
function comprobante(k) {
  const { F } = G;
  const [doc, d, prov] = k.split('|').map(Number);
  const ls = (porDoc(F).get(k) || []).slice().sort((a, b) => b.valor - a.valor);
  const tot = ls.reduce((s, l) => s + l.valor, 0), el = G.st.foco;
  return `<div class="lf-sub"><div class="dl-l enc"><span>${esc(F.docs[doc] || 'Comprobante')} · ${esc(F.provs[prov])} · ${fCorta(d)} · ${ls.length} ${ls.length === 1 ? 'línea' : 'líneas'}</span><span class="r">Cant.</span><span class="r">Precio</span><span class="r">Valor</span></div>`
    + ls.map((l) => `<div class="dl-l${l.prod === el ? ' sel' : ''}"><span title="${esc(F.nombres[l.prod])}">${esc(F.nombres[l.prod])}${l.flag ? ' <i class="w">⚠</i>' : ''}</span><span class="r">${cant(l.cant, F.um[l.prod])}</span><span class="r">${precio(l.cant ? l.valor / l.cant : null)}</span><span class="r">${soles(l.valor)}</span></div>`).join('')
    + `<div class="dl-l tot"><span>Total del comprobante</span><span></span><span></span><span class="r">${soles(tot)}</span></div></div>`;
}

function fichaHtml(V) {
  const { R, F, st } = G;
  const fila = R.P.find((p) => p.i === st.foco) || R.DEJ.find((p) => p.i === st.foco);
  if (!fila) return resumenHtml(V);
  const um = fila.um || '', h = F.L[fila.i], nom = F.nombres[fila.i], gran = st.gran, op = st.op, tab = st.tab, pw = st.pw;
  const subt = [];
  if (fila.ult != null) {
    let u = `última compra ${fCorta(fila.ult)}`;
    if (finito(fila.ultp)) u += ` a ${precio(fila.ultp)} / ${um || 'unidad'}`;
    subt.push(u);
    if (finito(fila.cada)) { const c = Math.round(fila.cada); subt.push(`cada ${c} ${c === 1 ? 'día' : 'días'}`); }
  }
  subt.push(`${fila.docs} ${fila.docs === 1 ? 'compra' : 'compras'} en el rango`);
  const cf = (rot, val, cls, sub, ayuda) => `<div class="lf-cf"${ayuda ? ` title="${esc(ayuda)}"` : ''}><span>${esc(rot)}</span><b class="${cls || ''}">${esc(val)}</b><small>${esc(sub)}</small></div>`;
  const cifras = cf('Compra', soles(fila.valor), '', fila.dej ? 'nada en el rango' : `${cant(fila.cant, um)} · ${(fila.valor / V.vT * 100).toFixed(1)} %`)
    + cf(`Vs. ${R.DIAS} días antes`, fila.est || (fila.dej ? '−100 %' : fmtVar(fila.var)), '', `${soles(fila.prev)} antes`, 'Comprar más o menos no es bueno ni malo: por eso va en gris.')
    + cf('Precio', precio(fila.pp), colorPrecio(fila.hab), finito(fila.hab) ? `${fmtVar(fila.hab)} contra lo habitual` : `/ ${um || 'unidad'}`, 'Soles ÷ cantidad, sin las compras para revisar.')
    + cf('Efecto del precio', finito(fila.ppv) && !fila.dej ? solesG(fila.ppv) : '—', colorPpv(fila.ppv), fila.ppv > 1 ? 'de más' : fila.ppv < -1 ? 'de ahorro' : 'igual a lo habitual', '(Precio pagado − habitual) × cantidad, en las compras del rango.');
  // La frase: si la compra cambió por cantidad o por precio, y a quién se le compra.
  const fr = [], pre = h.filter((l) => l.d >= R.R0 - R.DIAS && l.d < R.R0), qp = pre.reduce((a, l) => a + l.cant, 0), ok = pre.filter((l) => !l.flag && l.cant > 0), qok = ok.reduce((a, l) => a + l.cant, 0), pp0 = qok > 0 ? ok.reduce((a, l) => a + l.valor, 0) / qok : null;
  if (!fila.dej && qp > 0 && fila.cant > 0) {
    const dq = fila.cant / qp - 1, dp = finito(fila.pp) && pp0 ? fila.pp / pp0 - 1 : null;
    fr.push(`Compraste ${cant(fila.cant, um)} contra ${cant(qp, um)}${dp != null ? `; el precio ${Math.abs(dp) < 0.01 ? 'casi no se movió' : `${dp > 0 ? 'subió' : 'bajó'} ${Math.abs(dp * 100).toFixed(1)} %`}: la diferencia es de ${Math.abs(dq) >= Math.abs(dp) ? 'cantidad' : 'precio'}.` : '.'}`);
  }
  if (fila.dej) fr.push(`No se compró en este rango. Antes: ${soles(fila.prev)}, ${fila.n90} compras en 90 días.`);
  const g90 = new Map();
  h.forEach((l) => { if (l.d > R.R1 - 90 && l.d <= R.R1 && l.cant > 0 && !l.flag) { const a = g90.get(l.prov) || { prov: l.prov, v: 0, c: 0 }; a.v += l.valor; a.c += l.cant; g90.set(l.prov, a); } });
  const r90 = [...g90.values()].map((a) => ({ ...a, pu: a.v / a.c })).sort((a, b) => a.pu - b.pu);
  if (r90.length) {
    const may = [...r90].sort((a, b) => b.v - a.v)[0], tt = r90.reduce((a, x) => a + x.v, 0), sh = Math.round(may.v / tt * 100);
    if (r90.length === 1) fr.push(`En 90 días, un solo proveedor: ${F.provs[may.prov]}.`);
    else if (may.prov === r90[0].prov) fr.push(`${sh} % a ${F.provs[may.prov]}, el precio más bajo de los ${r90.length} de 90 días.`);
    else fr.push(`${sh} % a ${F.provs[may.prov]}; ${F.provs[r90[0].prov]} salió ${Math.round((1 - r90[0].pu / may.pu) * 100)} % más barato, por ${cant(r90[0].c, um)}.`);
  }
  if (fila.nflag) fr.push(`${fila.nflag} ${fila.nflag === 1 ? 'compra para revisar no entra' : 'compras para revisar no entran'} en el precio.`);
  const S = serie(h, gran, op, R.ULT, [R.R0, R.R1]);
  const per = S && S.keys.includes(st.per) ? st.per : null;
  G.S = S; G.gran = gran; G.um = um;
  const cprov = h.some((l) => l.prov === st.cprov) ? st.cprov : null;
  const lin = S ? S.lineas : [], bsel = per ? lin.filter((l) => l.k === per) : null;
  let Lp;
  if (pw === 'ven') Lp = bsel || lin;
  else { const p0 = pw === 'rango' ? R.R0 : R.R1 - 89; Lp = h.filter((l) => l.d >= p0 && l.d <= R.R1); }
  let Lc = bsel || (cprov != null ? Lp : h.filter((l) => l.d >= R.R0 && l.d <= R.R1));
  if (cprov != null) Lc = Lc.filter((l) => l.prov === cprov);
  const tPv = tablaProveedores(Lp, um), tCp = tablaCompras(Lc, um);
  const tabs = [['resumen', 'Resumen'], ['curva', 'Curva'], ['prov', `Proveedores · ${tPv.n}`], ['comp', `Compras · ${tCp.n}`], ['per', `Períodos · ${S ? S.keys.length : 0}`]]
    .map(([k, t]) => `<button class="${k === tab ? 'on' : ''}" data-acc="tab" data-v="${k}" aria-pressed="${k === tab}">${esc(t)}</button>`).join('');
  const chips = (tab === 'comp' && per ? `<button class="lf-quita" data-acc="soltar-per">${esc(etq(per, gran, true, F))} ✕</button>` : '')
    + (tab === 'comp' && cprov != null ? `<button class="lf-quita" data-acc="soltar-prov" title="${esc(F.provs[cprov])}">${esc(F.provs[cprov])} ✕</button>` : '');
  const op2 = (v, t, on) => `<option value="${v}"${on ? ' selected' : ''}>${t}</option>`;
  let zona;
  if (tab === 'resumen') {
    zona = `<section class="cpd-resumen" aria-label="Resumen del producto"><div class="lf-cifras">${cifras}</div>`
      + `${fr.length ? `<p class="lf-frase">${esc(fr.join(' '))}</p>` : ''}</section>`;
  } else if (tab === 'curva') {
    let graf;
    if (!S) graf = `<div class="lf-sinc">Sin compras de este producto en «${esc(OPS.find((o) => o[0] === op)[1])}».</div>`;
    else {
      const qs = S.agg.map((a) => a.c), ps = S.agg.map(precioDe), hs = S.agg.map(habDe), n = S.keys.length;
      graf = lfCurva({ etqs: S.keys.map((k) => esc(etq(k, gran, false, F))), ys: qs, claves: S.keys, acc: 'barra', parcial: !!S.parc, refY: S.parc ? S.refq : null, foco: per,
        rotY: (y, esPrecio) => (esPrecio ? precio(y) : ''), linea: ps, hab: hs, marcadas: S.agg.map((a) => a.fl > 0), banda: [8, 50] });
      if (S.parc && (S.agg[n - 1].c || S.refq)) G.notaC = `${S.parc.rot}: ${cant(S.agg[n - 1].c, um)} · ${S.parc.rotRef}: ${cant(S.refq, um)} ${fmtVar(varPct(S.agg[n - 1].c, S.refq))} · la raya negra marca los mismos días del período anterior`;
      else G.notaC = 'Al pasar el cursor, sus compras. Clic en una barra: sus compras abajo.';
    }
    zona = `<div class="lf-ev"><select class="lf-men" data-sel="gran" aria-label="Agrupar">${GRANOS.map(([k, t]) => op2(k, `Por: ${t}`, k === gran)).join('')}</select><select class="lf-men" data-sel="op" aria-label="Ventana de la curva">${OPS.map(([k, t]) => op2(k, `Curva: ${t}`, k === op)).join('')}</select><span class="lf-esp"></span>`
      + `<span class="lf-leyc"><span><i class="b"></i>${esc(um || 'unidades')}</span><span><i></i>precio</span><span><i class="h"></i>habitual</span>${S && S.agg.some((a) => a.fl) ? '<span><i class="f"></i>para revisar</span>' : ''}</span></div>${graf}${S ? `<p class="lf-nota">${esc(G.notaC)}</p>` : ''}`;
  } else if (tab === 'prov') {
    zona = `<div class="lf-ev"><select class="lf-men" data-sel="pw" aria-label="Comparar en">${[['rango', 'Comparar en: el rango'], ['90', 'Comparar en: 90 días'], ['ven', per ? `Comparar en: ${etq(per, gran, true, F)}` : 'Comparar en: la curva']].map(([k, t]) => op2(k, esc(t), k === pw)).join('')}</select><span class="sub">Clic: sus compras</span></div><div class="cuerpo">${tPv.html}</div>`
      + (tPv.n > 1 ? '<p class="lf-nota">Una diferencia grande puede ser otra calidad o presentación, no sólo precio.</p>' : '');
  } else if (tab === 'comp') {
    zona = `<div class="cuerpo">${tCp.html}</div><p class="lf-nota">Clic en una compra: el comprobante entero. En naranja, las compras para revisar: no entran en el precio.</p>`;
  } else {
    zona = `<div class="cuerpo">${S ? tablaPeriodos(S, gran, um, per) : '<div class="nota-v">Sin curva.</div>'}</div><p class="lf-nota">Una fila por barra de la curva. Clic: sus compras.</p>`;
  }
  return `<div class="lf-fcab"><div class="lf-ftit"><span class="lf-miga">${esc(nomS(R, fila.sub))} · ${esc(nomF(R, fila.fam))}${F.cods[fila.i] ? ` · cód. ${esc(F.cods[fila.i])}` : ''}</span><h3 title="${esc(nom)}">${esc(nom)}</h3><span class="lf-miga" title="${esc(subt.join(' · '))}">${esc(subt.join(' · '))}</span></div>`
    + `${lfAmp('panel', st.amp === 'panel', 'la ficha')}<button class="lf-quita" data-acc="soltar">Soltar</button></div>`
    + `<div class="lf-fl"><span class="lf-seg" role="group" aria-label="Qué mirar">${tabs}</span>${chips}</div><div class="lf-zona">${zona}</div>`;
}

// El globo de un período: la cifra y sus compras.
function pintarTip(k) {
  const raiz = G.raiz, S = G.S;
  if (!raiz || !S) return;
  const i = k == null ? -1 : S.keys.indexOf(k);
  if (i < 0) { lfTip(raiz, null); return; }
  const { F } = G, um = G.um, gran = G.gran, a = S.agg[i], p = precioDe(a), parc = S.parc && i === S.keys.length - 1, fila = (x, y) => `<span><i>${esc(x)}</i>${esc(y)}</span>`;
  let html = `<b>${esc(etq(k, gran, true, F))}${parc ? ' (en curso)' : ''}</b>${fila('Cantidad', cant(a.c, um))}${fila('Precio', precio(p))}${fila('Compra', `${soles(a.v)} · ${a.docs} ${a.docs === 1 ? 'compra' : 'compras'}`)}`;
  if (a.fl) html += fila('Para revisar', `${a.fl}, fuera del precio`);
  const ds = porDocumento(S.lineas.filter((l) => l.k === k)).sort((x, y) => y.d - x.d);
  html += ds.slice(0, FILAS_TIP).map((x) => fila(`${fCorta(x.d)} · ${F.provs[x.prov]}`, `${precio(x.cant ? x.valor / x.cant : null)}${x.flag ? ' ⚠' : ''}`)).join('');
  if (ds.length) html += `<em>${ds.length > FILAS_TIP ? `y ${ds.length - FILAS_TIP} más · ` : ''}clic: sus compras</em>`;
  lfTip(raiz, i, S.keys.length, html);
}

function pintar() {
  const { R, F, st } = G, raiz = G.raiz;
  if (!raiz) return;
  if (!st.pleg) st.pleg = {};
  if (!R || !F || R.sello !== F.sello) { if (!raiz.innerHTML) raiz.innerHTML = '<div class="lf-vacio">Cargando…</div>'; return; }
  const V = vista(R, F, st);
  G.V = V;
  const yL = raiz.querySelector('[data-tabla="lista"]')?.scrollTop || 0, yF = raiz.querySelector('.ft-l')?.scrollTop || 0, yR = raiz.querySelector('.lf-lista')?.scrollTop || 0;
  const foco = raiz.querySelector('.lf-busca:focus'), sel = foco ? [foco.selectionStart, foco.selectionEnd] : null;
  const verIzq = st.amp !== 'panel', verPanel = st.amp !== 'izq';
  const vers = [['todos', `Todos · ${ent(V.base.length)}`, ''], ['n80', `Hacen el 80 % · ${V.en80.size}`, 'Los que suman el 80 % de lo comprado'], ['fam', 'Por familia', 'Familia › Subfamilia › Producto']];
  const chip = (st.kpi !== 'todos' ? `<button class="lf-quita" data-acc="kpi" data-v="${st.kpi}">${{ nv: 'Nuevos o vuelven', dej: 'Se dejaron', rev: 'Para revisar' }[st.kpi]} ✕</button>` : '')
    + (st.sub ? `<button class="lf-quita" data-acc="soltar-sub">${esc(nomS(R, st.sub[1]))} ✕</button>` : '');
  const hasta = st.ver === 'fam' ? `<select class="lf-men" data-sel="hasta" aria-label="Abrir hasta">${[['0', 'Familia'], ['1', 'Subfamilia'], ['2', 'Producto']].map(([k, t]) => `<option value="${k}"${k === st.hasta ? ' selected' : ''}>Abrir hasta: ${t}</option>`).join('')}</select>` : '';
  let h = `<div class="lf-main${st.det ? ' det' : ''}${st.amp ? ' amp' : ''}">${lfNivel2(vers, st.ver, st.det, st.como, comoHtml(R))}`
    + `<div class="lf-cab"><span class="lf-lugar" aria-hidden="true"></span>${lfMenuFamilias(R.pagina, st.menu === 'fam', soles, esc)}${hasta}${chip}<span class="lf-esp"></span>`
    + `<input class="lf-busca" type="search" value="${esc(st.q || '')}" placeholder="Buscar producto o código…" aria-label="Buscar producto o código"><button class="lf-pil" data-acc="excel" title="Baja lo que se ve">Excel ↓</button></div>`
    + `<div class="lf-kpis">${kpisHtml(V, R, F)}</div><div class="lf-cuerpo" data-amp="${st.amp || ''}">`;
  if (verIzq) h += `<div class="lf-izq">${listaHtml(V)}</div>`;
  if (verPanel) h += `<aside class="lf-panel" aria-label="Ficha">${st.foco != null ? fichaHtml(V) : resumenHtml(V)}</aside>`;
  raiz.innerHTML = `${h}</div></div>`;
  const pon = (q, y) => { const e = raiz.querySelector(q); if (e) e.scrollTop = y; };
  pon('[data-tabla="lista"]', yL);
  if (G.reseteaF) G.reseteaF = false; else pon('.ft-l', yF);
  pon('.lf-lista', yR);
  if (sel) { const e = raiz.querySelector('.lf-busca'); e.focus({ preventScroll: true }); e.setSelectionRange(...sel); }
  lfPasarFecha(raiz, '.st-key-cp_prod_nativa_fecha');
}

// ── Los clics ────────────────────────────────────────────────────────────
function avisarFamilias() {
  if (G.pendFam && G.enviar) { const x = G.pendFam; G.pendFam = null; G.enviar('familias', x); }
}
function accion(acc, val, b) {
  const st = G.st;
  if (acc === 'menu') { st.menu = st.menu === val ? null : val; if (!st.menu) avisarFamilias(); pintar(); return; }
  if (st.menu) { st.menu = null; avisarFamilias(); }
  if (acc !== 'como') st.como = false;
  if (acc === 'detalle') { st.det = !!(b && b.checked); lfGuardar('cp_prod_det', st.det); }
  else if (acc === 'como') st.como = !st.como;
  else if (acc === 'pleg') { st.pleg = { ...st.pleg, [val]: st.pleg[val] === false }; lfGuardar('cp_prod_pleg', st.pleg); }
  else if (acc === 'orden') {
    const s = st.sort, d0 = val === 'nom' ? 1 : -1;
    st.sort = !s || s.col !== val ? { col: val, dir: d0 } : s.dir === d0 ? { col: val, dir: -s.dir } : null;
  } else if (acc === 'fila') {
    const i = +val;
    st.foco = st.foco === i ? null : i; st.per = null; st.cprov = null; st.doc = null; G.reseteaF = true;
    if (st.amp === 'izq') st.amp = null;
    if (st.foco == null && st.amp === 'panel') st.amp = null;
  } else if (acc === 'grupo') { const n = +b.dataset.n; const ab = st.ab[val] != null ? st.ab[val] : n < +st.hasta; st.ab = { ...st.ab, [val]: !ab }; }
  else if (acc === 'excel') { excel(); return; }
  else if (acc === 'kpi') { st.kpi = st.kpi === val ? 'todos' : val; st.foco = null; st.sort = null; }
  else if (acc === 'ver') { st.ver = val; st.sort = null; }
  else if (acc === 'sub') { const [f, s] = val.split('\u001f'); st.sub = st.sub && st.sub[0] === f && st.sub[1] === s ? null : [f, s]; st.foco = null; }
  else if (acc === 'soltar-sub') st.sub = null;
  else if (acc === 'amp') st.amp = st.amp === val ? null : val;
  else if (acc === 'soltar') { st.foco = null; st.per = null; st.cprov = null; st.doc = null; if (st.amp === 'panel') st.amp = null; }
  else if (acc === 'soltar-per') st.per = null;
  else if (acc === 'soltar-prov') st.cprov = null;
  else if (acc === 'sumar') { const pa = G.R.pagina; pa.elegidas = pa.todas.map((x) => x[0]); G.pendFam = pa.elegidas.slice(); avisarFamilias(); return; }
  else if (acc === 'tab') { st.tab = val; G.reseteaF = true; }
  else if (acc === 'barra' || acc === 'per') { st.per = st.per === val && acc === 'per' ? null : val; st.cprov = null; st.tab = 'comp'; G.reseteaF = true; }
  else if (acc === 'prov') { st.cprov = +val; st.tab = 'comp'; if (st.pw !== 'ven') st.per = null; G.reseteaF = true; }
  else if (acc === 'doc') st.doc = st.doc === val ? null : val;
  else return;
  pintar();
}
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.disabled) {
      if (G.st.menu && !(ev.target.closest && ev.target.closest('.lf-ms'))) { G.st.menu = null; avisarFamilias(); pintar(); }
      else if (G.st.como && !(ev.target.closest && ev.target.closest('.lf-como'))) { G.st.como = false; pintar(); }
      return;
    }
    accion(b.dataset.acc, b.dataset.v, b);
  });
  raiz.addEventListener('input', (ev) => {
    if (!ev.target.classList.contains('lf-busca')) return;
    G.st.q = ev.target.value;
    pintar();
  });
  raiz.addEventListener('change', (ev) => {
    const t = ev.target, st = G.st;
    if (t.matches('[data-pfam]')) {
      const pa = G.R.pagina, el = pa.elegidas.length ? pa.elegidas : pa.todas.map((x) => x[0]);
      pa.elegidas = t.checked ? [...el, t.value] : el.filter((x) => x !== t.value);
      G.pendFam = pa.elegidas.slice();
      pintar();
      return;
    }
    const k = t.dataset && t.dataset.sel;
    if (!k) return;
    st[k] = t.value;
    if (k === 'hasta') st.ab = {};
    if (k === 'gran' || k === 'op') st.per = null;
    pintar();
  });
  raiz.addEventListener('mouseover', (ev) => {
    const b = ev.target.closest('[data-acc="barra"]');
    if (b && raiz.contains(b)) pintarTip(b.dataset.v);
  });
  raiz.addEventListener('mouseout', (ev) => {
    const b = ev.target.closest('[data-acc="barra"]');
    if (b && !(ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest('[data-acc="barra"]'))) pintarTip(null);
  });
  raiz.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && G.st.menu) { G.st.menu = null; avisarFamilias(); pintar(); }
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.parte) return;
  if (data.parte === 'ficha') {
    if (!G.F || G.F.sello !== data.sello) { G.F = leerFicha(data); G.spark = null; }
  } else {
    let raiz = parentElement.querySelector('.cpd');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'lf cpd';
      parentElement.appendChild(raiz);
      enlazar(raiz);
      lfEscape(G, pintar);
      // La fecha de Python sigue a su hueco si cambia el ancho.
      new ResizeObserver(() => lfPasarFecha(raiz, '.st-key-cp_prod_nativa_fecha')).observe(raiz);
    }
    G.raiz = raiz;
    G.enviar = setTriggerValue;
    if (G.rankData !== data) {
      G.rankData = data;
      G.R = leerRank(data);
      G.spark = null;
    }
  }
  pintar();
}

window.__cpProdCalc = { leerFicha, leerRank, vista, serie, dn };
