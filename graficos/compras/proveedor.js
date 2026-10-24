// Compras › Proveedor (regla #715).
//
// La monta graficos/compras/proveedor.py con st.components.v2 (sin iframe,
// estilos en un shadow root) DOS VECES, una en cada tarjeta: la del ranking
// (`parte: "rank"`: el rango y el filtro de proveedores) y la de la ficha
// (`parte: "ficha"`: el historial de líneas, por proveedor). `_xlsx.js` va
// antepuesto (libro, bajar, archivo).
//
// UN CEREBRO, DOS MONTAJES, como Producto (#713): `window.__cpProv` guarda
// los datos de las dos, el estado de lo elegido y las dos raíces, y dibuja
// cuando tiene las dos con la MISMA `sello`. El estado vive ahí y no en la
// raíz: sobrevive a que Streamlit vuelva a montar la pieza.
//
// Nada vuelve a Python: el proveedor elegido, el producto en foco, la
// ventana, el grano y la medida de la curva, las pestañas, lo desplegado y
// el Excel los resuelve el navegador. Sólo la fecha y el filtro de
// proveedores (arriba de la pieza, de Python) piden una corrida.
//
// Las cuentas son las de la vista de antes (regla #646): `_contra_anterior`
// y `_estado` del ranking, `_ppv`, la curva con `periodo.ventana`,
// `inicio_de_periodo` y `tramo_parcial`, `_html_desglose`, `_historia_docs`.
// Lo vigila test_proveedor_pieza.py, que corre `calcular` en Chromium contra
// las mismas cuentas en pandas.

const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIA = 864e5;
// Una línea del historial (proveedor.historial_pieza).
const RL = { dia: 0, prod: 1, doc: 2, cant: 3, valor: 4, ref: 5, um: 6 };
const GRANOS = [['Día', 'Día'], ['Semana', 'Semana'], ['Mes', 'Mes'], ['Año', 'Año'], ['Documento', 'Doc.']];
const GRAN_POR = { Día: 'Por día', Semana: 'Por semana', Mes: 'Por mes', Año: 'Por año', Documento: 'Por documento' };
const MEDIDAS = [['valor', 'Soles'], ['cant', 'Cantidad'], ['precio', 'Precio']];
const OPS = [['Rango', 'El rango del ranking'], ['3m', 'Últimos 3 meses'], ['12m', 'Últimos 12 meses'],
  ['24m', 'Últimos 24 meses'], ['Todo', 'Todo el histórico']];
const MESES_OP = { '3m': 3, '12m': 12, '24m': 24 };
const VENTANA_AUTO = 12;   // max(4, min(12, int(1200 / (16 * 2)))) de la vista de antes
const UMBRAL_PRECIO = 2.0; // % que pinta una celda de precio del Desglose (umbral PROPIO, #646)
const N_COLORES = 7;       // --serie-0 … --serie-6 de estilos/_00_base.py

// ── Fechas como número de día (UTC) ──────────────────────────────────────
const dn = (s) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d) / DIA; };
const ymd = (n) => { const t = new Date(n * DIA); return [t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()]; };
const iso = (n) => { const [y, m, d] = ymd(n); return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
const diaSemana = (n) => (new Date(n * DIA).getUTCDay() + 6) % 7;
const fCorta = (n) => { const [, m, d] = ymd(n); return `${d} ${MES[m - 1]}`; };
const fDMA = (n) => { const [y, m, d] = ymd(n); return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${String(y).slice(2)}`; };
const fDM = (n) => { const [, m, d] = ymd(n); return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}`; };
const mesAnio = (n) => { const [y, m] = ymd(n); return `${MES[m - 1]} ${y}`; };

// ── Formato (los de la vista de antes) ───────────────────────────────────
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const finito = (v) => v != null && isFinite(v);
const num = (v, dec) => v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
const soles = (v) => (finito(v) ? `${v < -0.5 ? '−' : ''}S/ ${num(Math.abs(v), 0)}` : '—');
const precio = (v) => (finito(v) ? `S/ ${num(v, 2)}` : '—');
const cantTxt = (c) => num(c, 2).replace(/\.?0+$/, '');
const sk = (v) => (v >= 1000 ? `S/ ${num(v / 1000, 1)}k` : `S/ ${num(v, 0)}`);
// `_var_pct`: null si no hay contra qué (desde cero no hay porcentaje).
const varPct = (cur, prev) => (finito(prev) && prev > 0 && finito(cur) ? (cur - prev) / prev * 100 : null);
const fmtVar = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.05 ? '0.0%' : `${v > 0 ? '▲' : '▼'} ${Math.abs(v).toFixed(1)}%`);
// Rojo si subió el gasto, verde si bajó; sin color por debajo del 0,5 %.
const clsVar = (v) => (!finito(v) || Math.abs(v) < 0.5 ? '' : v > 0 ? 'sube' : 'baja');
const filaVar = (v) => `<span class="var ${clsVar(v)}">${fmtVar(v)}</span>`;
const trunc = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
const sinTildes = (s) => String(s).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
const suma = (xs, f) => xs.reduce((s, x) => s + f(x), 0);
const color = (i) => (i == null || i < 0 ? 'var(--border)' : `var(--serie-${i % N_COLORES})`);

// La unidad más frecuente; empatadas, la MENOR (`moda_por_grupo`). Sin
// unidad no cuenta.
function moda(ls, F) {
  const n = new Map();
  ls.forEach((l) => { if (F.umsRaw[l.um]) n.set(l.um, (n.get(l.um) || 0) + 1); });
  let mejor = null, k = 0;
  n.forEach((c, u) => { if (c > k || (c === k && u < mejor)) { mejor = u; k = c; } });
  return mejor == null ? '' : F.ums[mejor];
}

// ── Los períodos (`agregar_periodo`, `inicio_de_periodo`, `tramo_parcial`) ─
// La CLAVE de un período ordena; en «Documento» es la fecha y el número
// (el índice en `docs`, que va ordenada por el texto del parquet).
function clave(l, gran) {
  const [y, m] = ymd(l.d);
  if (gran === 'Día') return iso(l.d);
  if (gran === 'Semana') return iso(l.d - diaSemana(l.d));
  if (gran === 'Mes') return `${y}-${String(m).padStart(2, '0')}`;
  if (gran === 'Año') return String(y);
  return l.sinDoc ? null : `${iso(l.d)}|${String(l.doc).padStart(6, '0')}`;
}
function inicioDe(n, gran) {
  const [y, m] = ymd(n);
  if (gran === 'Mes') return Date.UTC(y, m - 1, 1) / DIA;
  if (gran === 'Semana') return n - diaSemana(n);
  if (gran === 'Año') return Date.UTC(y, 0, 1) / DIA;
  return n;
}
function restarMeses(n, k) {
  const [y, m, d] = ymd(n);
  const t = new Date(Date.UTC(y, m - 1 - k, 1));
  const ult = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth() + 1, 0)).getUTCDate();
  return Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), Math.min(d, ult)) / DIA;
}
// periodo.ventana: contada desde el último día CON DATOS, +1 día.
function ventana(op, ultimo, minimo) {
  if (op === 'Todo') return [Math.min(minimo, ultimo), ultimo];
  let ini = restarMeses(ultimo, MESES_OP[op]) + 1;
  if (minimo > ini) ini = minimo;
  return [ini, ultimo];
}
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
// El rótulo de un período a partir de su clave (`_etq`).
function etq(k, gran, corta, F) {
  if (gran === 'Mes') { const [y, m] = k.split('-').map(Number); return `${MES[m - 1]} ${String(y).slice(2)}`; }
  if (gran === 'Semana' || gran === 'Día') return fCorta(dn(k));
  if (gran === 'Documento') { const leg = F.docs[+k.split('|')[1]] || ''; return corta ? leg.split('-').pop() : leg; }
  return k;
}

// ── Los datos ────────────────────────────────────────────────────────────
function leerFicha(data) {
  const base = dn(data.base);
  const vacio = new Set(['', 'nan', 'None']);
  const P = data.lineas.map((ls, p) => ls.map((l) => ({
    p, d: base + l[RL.dia], prod: l[RL.prod], doc: l[RL.doc], cant: l[RL.cant] || 0, valor: l[RL.valor] || 0,
    ref: l[RL.ref], um: l[RL.um], sinDoc: !data.docs[l[RL.doc]] })));
  const todas = P.flat();
  let min = Infinity;
  todas.forEach((l) => { if (l.d < min) min = l.d; });
  return { sello: data.sello, ULT: dn(data.ultimo), MIN: min, provs: data.provs, noms: data.noms, prods: data.prods,
    docs: data.docs, ums: data.ums, umsRaw: data.ums.map((u) => !vacio.has(u)), P, todas, alto: data.alto_curva || 150,
    porProd: null };
}
function leerRank(data) {
  return { sello: data.sello, R0: dn(data.rango[0]), R1: dn(data.rango[1]), sel: data.sel || [], otros: !!data.otros };
}
// Las líneas de un producto, de todos los proveedores (se arma una vez).
function delProducto(F, i) {
  if (!F.porProd) {
    F.porProd = new Map();
    F.todas.forEach((l) => { if (!F.porProd.has(l.prod)) F.porProd.set(l.prod, []); F.porProd.get(l.prod).push(l); });
  }
  return F.porProd.get(i) || [];
}

// ── Las cuentas (puras: las corre también el test) ──────────────────────
// El ranking del rango: `_contra_anterior`, `_estado` y la fila TOTAL.
function ranking(F, R) {
  const dias = R.R1 - R.R0 + 1, p0 = R.R0 - dias;
  const n = F.provs.length;
  const val = new Array(n).fill(0), prev = new Array(n).fill(0), ult = new Array(n).fill(null), hay = new Array(n).fill(false);
  F.todas.forEach((l) => {
    if (l.d >= R.R0 && l.d <= R.R1) { val[l.p] += l.valor; hay[l.p] = true; } else if (l.d < R.R0) {
      if (l.d >= p0) prev[l.p] += l.valor;
      if (ult[l.p] == null || l.d > ult[l.p]) ult[l.p] = l.d;
    }
  });
  const enRango = [];
  for (let p = 0; p < n; p += 1) if (hay[p]) enRango.push(p);
  enRango.sort((a, b) => val[b] - val[a] || a - b);
  const totAll = suma(enRango, (p) => val[p]) || 1;
  const defecto = enRango.length ? enRango[0] : null;
  const elegidos = new Set(R.sel);
  let top = enRango.filter((p) => elegidos.has(F.provs[p]));
  if (!top.length) top = enRango;
  const enTop = new Set(top);
  const fuera = enRango.filter((p) => !enTop.has(p));
  const estado = (p) => {
    if (prev[p] > 0) return { var: varPct(val[p], prev[p]), est: '', ayuda: '' };
    if (ult[p] == null) return { var: null, est: 'nuevo', ayuda: 'Primera compra en este rango' };
    const [y, m, d] = ymd(ult[p]);
    return { var: null, est: 'vuelve', ayuda: `Sin compras desde el ${d} ${MES[m - 1]} ${y}` };
  };
  const filas = top.map((p) => ({ p, valor: val[p], pct: val[p] / totAll * 100, prev: prev[p], ...estado(p) }));
  if (R.otros && fuera.length) {
    const v = suma(fuera, (p) => val[p]);
    filas.push({ p: -1, valor: v, pct: v / totAll * 100, prev: suma(fuera, (p) => prev[p]), var: null, est: '', ayuda: '', otros: fuera.length });
  }
  const vTot = suma(filas, (f) => f.valor);
  const vals = filas.map((f) => f.valor).sort((a, b) => b - a);
  let acum = 0, n80 = 0;
  vals.forEach((v) => { acum += v; if (acum / totAll * 100 < 80) n80 += 1; });
  return { filas, defecto, top, totAll, dias, n80: vals.length ? n80 + 1 : 0,
    total: { n: filas.length, valor: vTot, pct: suma(filas, (f) => f.pct), var: varPct(vTot, suma(filas, (f) => f.prev)) } };
}

// Las cifras del rango de un proveedor y el «vs. precio habitual» (`_ppv`):
// (precio pagado − habitual) × cantidad, y el % por producto.
function cifras(F, R, p) {
  const ls = F.P[p].filter((l) => l.d >= R.R0 && l.d <= R.R1);
  const compra = suma(ls, (l) => l.valor);
  const docs = new Set(ls.filter((l) => !l.sinDoc).map((l) => l.doc)).size;
  let ppv = 0, hay = false;
  const porProd = new Map();
  ls.forEach((l) => {
    if (!finito(l.ref) || !(l.cant > 0) || !(l.valor > 0)) return;
    hay = true;
    const x = l.valor - l.ref * l.cant;
    ppv += x;
    const a = porProd.get(l.prod) || { ppv: 0, vref: 0 };
    a.ppv += x; a.vref += l.ref * l.cant;
    porProd.set(l.prod, a);
  });
  const hab = new Map();
  porProd.forEach((a, k) => hab.set(k, a.vref > 0 ? a.ppv / a.vref * 100 : null));
  return { ls, compra, docs, ppv: hay ? ppv : null, hab };
}

// La curva de la ficha: los períodos, el valor de cada uno en la medida, el
// tramo en curso y los mismos días del anterior. `src` son las líneas de
// TODOS los proveedores de la ventana (la regla #646: los períodos son los
// del rango entero, no los del proveedor).
function curvaDe(F, R, st, p, prod) {
  const gran = st.gran, op = st.op;
  let hist = op !== 'Rango', ini, fin;
  if (hist) { [ini, fin] = ventana(op, F.ULT, F.MIN); ini = inicioDe(ini, gran); } else { ini = R.R0; fin = R.R1; }
  let src = F.todas.filter((l) => l.d >= ini && l.d <= fin);
  if (hist && !src.length) { hist = false; src = F.todas.filter((l) => l.d >= R.R0 && l.d <= R.R1); }
  src.forEach((l) => { l.k = clave(l, gran); });
  src = src.filter((l) => l.k != null);
  const deP = src.filter((l) => l.p === p);
  const claves = (ls) => [...new Set(ls.map((l) => l.k))].sort();
  let keys = gran === 'Documento' ? claves(deP) : claves(src);
  let win = null;
  if (!hist && gran !== 'Documento') {
    const nPer = Math.max(1, keys.length);
    const ops = [null, ...[1, 2, 3, 6, 12, 24].filter((o) => o < nPer), nPer];
    const tam = ops.includes(st.win) ? st.win : null;
    let ven = tam == null ? VENTANA_AUTO : Math.min(tam, nPer);
    ven = Math.max(1, Math.min(ven, nPer));
    const iniMax = Math.max(0, nPer - ven), firma = `${gran}|${nPer}|${ven}`;
    if (st.winFirma !== firma) { st.winFirma = firma; st.winIni = iniMax; }
    st.winIni = Math.min(Math.max(0, st.winIni ?? iniMax), iniMax);
    keys = keys.slice(st.winIni, st.winIni + ven);
    win = { ops, tam, ven, ini: st.winIni, iniMax, nPer };
  }
  const medida = prod != null ? st.medida : 'valor';
  const deCurva = prod != null ? deP.filter((l) => l.prod === prod) : deP;
  const idx = new Map(keys.map((k, i) => [k, i]));
  const v = keys.map(() => 0), c = keys.map(() => 0), tot = keys.map(() => 0), docs = keys.map(() => new Set());
  src.forEach((l) => { const i = idx.get(l.k); if (i != null) tot[i] += l.valor; });
  deCurva.forEach((l) => {
    const i = idx.get(l.k);
    if (i == null) return;
    v[i] += l.valor; c[i] += l.cant;
    if (!l.sinDoc) docs[i].add(l.doc);
  });
  const ys = keys.map((k, i) => (medida === 'cant' ? c[i] : medida === 'precio' ? (c[i] > 0 ? v[i] / c[i] : null) : v[i]));
  let parc = parcial(gran, F.ULT);
  if (parc && clave({ d: F.ULT }, gran) !== keys[keys.length - 1]) parc = null;
  let ref = null;
  const H = prod != null ? F.P[p].filter((l) => l.prod === prod) : F.P[p];
  if (parc && medida !== 'precio') {
    const r = H.filter((l) => l.d >= parc.refIni && l.d <= parc.refFin);
    ref = medida === 'cant' ? suma(r, (l) => l.cant) : suma(r, (l) => l.valor);
  }
  const um = prod != null ? moda(deCurva, F) : '';
  return { keys, ys, v, c, tot, docs: docs.map((s) => s.size), medida, parc, ref, um, hist, win, src, deP, gran, op };
}

// «Desglose»: una fila por producto, los últimos seis puntos de la curva en
// la medida de la ficha, con la tendencia de trece (`_html_desglose`).
function desglose(F, C, H, medidaFicha) {
  const tend = C.keys.slice(-Math.min(13, C.keys.length)), vis = tend.slice(-6);
  const it = new Map(tend.map((k, i) => [k, i]));
  const g = new Map();
  C.deP.forEach((l) => {
    const i = it.get(l.k);
    if (i == null) return;
    const a = g.get(l.prod) || { prod: l.prod, v: tend.map(() => 0), c: tend.map(() => 0), ls: [] };
    a.v[i] += l.valor; a.c[i] += l.cant; a.ls.push(l);
    g.set(l.prod, a);
  });
  const nv = vis.length, desde = tend.length - nv;
  const sVis = (a) => a.v.slice(desde).reduce((s, x) => s + x, 0);
  const filas = [...g.values()].filter((a) => sVis(a) > 0).sort((a, b) => sVis(b) - sVis(a));
  const medida = medidaFicha;
  filas.forEach((a) => {
    a.m = tend.map((k, i) => (medida === 'cant' ? a.c[i] : medida === 'precio' ? (a.c[i] > 0 ? a.v[i] / a.c[i] : null) : a.v[i]));
    a.um = medida !== 'valor' ? moda(a.ls, F) : '';
  });
  let refV = new Map(), refC = new Map();
  if (C.parc) {
    H.filter((l) => l.d >= C.parc.refIni && l.d <= C.parc.refFin).forEach((l) => {
      refV.set(l.prod, (refV.get(l.prod) || 0) + l.valor);
      refC.set(l.prod, (refC.get(l.prod) || 0) + l.cant);
    });
  }
  const modo = C.parc ? (medida === 'precio' ? 'prev' : 'ref')
    : ((C.gran === 'Día' || C.gran === 'Documento') && medida !== 'precio' ? 'nada' : 'prev');
  const total = medida === 'valor' ? vis.map((k) => suma(C.deP.filter((l) => l.k === k), (l) => l.valor)) : null;
  return { tend, vis, filas, refV, refC, modo, total, medida };
}

// Los documentos del historial de un proveedor: los días desde la compra
// anterior y el producto que más subió de precio contra su compra anterior
// al MISMO proveedor (`_historia_docs`).
function historiaDocs(H) {
  const fecha = new Map();
  H.forEach((l) => { if (!l.sinDoc && (!fecha.has(l.doc) || l.d < fecha.get(l.doc))) fecha.set(l.doc, l.d); });
  const orden = [...fecha.entries()].sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  const dias = new Map();
  orden.forEach(([doc, d], i) => dias.set(doc, i ? d - orden[i - 1][1] : null));
  const lin = new Map();
  H.forEach((l) => {
    if (l.sinDoc || !(l.cant > 0)) return;
    const k = `${l.doc}|${l.prod}`;
    const a = lin.get(k) || { doc: l.doc, prod: l.prod, v: 0, c: 0, f: l.d };
    a.v += l.valor; a.c += l.cant; a.f = Math.min(a.f, l.d);
    lin.set(k, a);
  });
  const xs = [...lin.values()].filter((a) => a.c > 0)
    .sort((a, b) => a.prod - b.prod || a.f - b.f || a.doc - b.doc);
  const sube = [];
  xs.forEach((a, i) => {
    a.pu = a.v / a.c;
    const ant = i && xs[i - 1].prod === a.prod ? xs[i - 1].pu : null;
    const dp = ant ? (a.pu / ant - 1) * 100 : null;
    if (dp != null && dp > 0.5) sube.push({ ...a, dp });
  });
  sube.sort((a, b) => b.dp - a.dp);
  const top = new Map(), nSube = new Map();
  sube.forEach((a) => { if (!top.has(a.doc)) top.set(a.doc, a); nSube.set(a.doc, (nSube.get(a.doc) || 0) + 1); });
  return { dias, top, nSube };
}

// Todo junto, para el test: lo que la pieza dibuja con un estado dado.
function calcular(F, R, st) {
  const rk = ranking(F, R);
  // El foco, si compró en el rango; si no, el que más (la fila de arriba).
  const p = st.foco != null && F.P[st.foco] && F.P[st.foco].some((l) => l.d >= R.R0 && l.d <= R.R1) ? st.foco : rk.defecto;
  if (p == null) return { rk };
  const ci = cifras(F, R, p);
  const prods = new Set(ci.ls.map((l) => l.prod));
  const prod = st.prod != null && prods.has(st.prod) ? st.prod : null;
  const C = curvaDe(F, R, st, p, prod);
  return { rk, p, prod, ci, C };
}

window.__cpProvCalc = { leerFicha, leerRank, ranking, cifras, curvaDe, desglose, historiaDocs, calcular, clave, parcial };

const G = window.__cpProv || (window.__cpProv = {
  st: { gran: 'Mes', op: '12m', medida: 'valor', tab: 'prod', pmodo: 'tot', dmodo: 'doc', abiertos: new Set() },
  R: null, F: null, raices: {} });

// ── El ranking ───────────────────────────────────────────────────────────
function pintarRank() {
  const raiz = G.raices.rank;
  if (!raiz) return;
  const { F, st } = G, X = G.X;
  const rk = X.rk;
  const elegido = X.p;
  const max = Math.max(1, ...rk.filas.map((f) => f.valor));
  const s = st.sort;
  const filas = rk.filas.slice();
  if (s) {
    const k = { nom: (f) => (f.p < 0 ? '~' : sinTildes(F.noms[f.p])), val: (f) => f.valor, pct: (f) => f.valor,
      var: (f) => (f.est ? (s.dir > 0 ? 1e15 : -1e15) : finito(f.var) ? f.var : -1e16) }[s.col];
    filas.sort((a, b) => { const x = k(a), y = k(b); return (x < y ? -1 : x > y ? 1 : 0) * s.dir; });
  }
  const col = s && s.col, dir = s && s.dir;
  const cab = [['nom', 'Proveedor', '', ''], ['val', 'Valor', '', 'r'], ['var', 'Δ', 'Contra el período anterior de igual largo', 'r'],
    ['pct', '%', '% del total comprado en el rango', 'r']];
  let html = '<div class="rk-f rk-h">' + cab.map(([k, t, ayuda, al]) =>
    `<button class="${al}" data-acc="orden" data-v="${k}" title="${esc(ayuda)}">${esc(t)}${col === k ? (dir > 0 ? ' ↑' : ' ↓') : ''}</button>`).join('')
    + '</div><div class="rk-l">';
  html += filas.map((f) => {
    const otros = f.p < 0;
    const nom = otros ? `Otros · ${f.otros}` : F.noms[f.p];
    const sel = !otros && f.p === elegido;
    const varTxt = f.est || fmtVar(f.var);
    const varCls = f.est || clsVar(f.var);
    return `<div class="rk-f${sel ? ' sel' : ''}${otros ? ' otros' : ''}"${otros ? '' : ` data-acc="fila" data-v="${f.p}"`} title="${esc(nom)}">`
      + `<span class="nm">${esc(nom)}</span>`
      + `<span class="r val" style="--b:${(Math.max(0, Math.min(1, f.valor / max)) * 100).toFixed(1)}%">${soles(f.valor)}</span>`
      + `<span class="r b ${varCls}" title="${esc(f.ayuda)}">${esc(varTxt)}</span>`
      + `<span class="r">${Math.round(f.pct)}%</span></div>`;
  }).join('');
  if (!filas.length) html += '<div class="vacio">Sin proveedores en el rango.</div>';
  const t = rk.total;
  html += '</div><div class="rk-f rk-t">'
    + `<span class="nm">TOTAL · ${t.n}</span><span class="r">${soles(t.valor)}</span>`
    + `<span class="r ${clsVar(t.var)}">${fmtVar(t.var)}</span><span class="r">${Math.round(t.pct)}%</span></div>`;
  raiz.querySelector('.tabla').innerHTML = html;
  raiz.querySelector('.pie span').textContent = `${rk.n80} ${rk.n80 === 1 ? 'proveedor hace' : 'proveedores hacen'} el 80 % de lo `
    + 'comprado · Δ: contra el período anterior de igual largo';
  const fsel = raiz.querySelector('.rk-f.sel');
  if (fsel && G.scrollAlSel) { fsel.scrollIntoView({ block: 'nearest' }); G.scrollAlSel = false; }
}

function excelRank() {
  const { F, R } = G, rk = G.X.rk;
  const filas = rk.filas.map((f) => [f.p < 0 ? `Otros (${f.otros})` : F.noms[f.p], f.valor, f.prev, f.var, f.est, f.pct]);
  filas.push([`TOTAL · ${rk.total.n}`, rk.total.valor, null, rk.total.var, '', rk.total.pct]);
  bajar(`compras_proveedores_${iso(R.R0)}_${iso(R.R1)}.xlsx`, libro([{ nombre: 'Ranking de proveedores',
    cabeza: ['Proveedor', 'Valor (S/)', `Período anterior (${rk.dias} días antes, S/)`, 'Δ % vs. período anterior', 'Estado', '% del total'], filas }]));
}

// ── La ficha ─────────────────────────────────────────────────────────────
const celda = (t, cls, ayuda) => `<span class="${cls || ''}"${ayuda ? ` title="${esc(ayuda)}"` : ''}>${t}</span>`;

function kpis(F, R, X) {
  const { rk, p, ci } = X;
  const f = rk.filas.find((x) => x.p === p) || { ...ranking(F, { ...R, sel: [F.provs[p]], otros: false }).filas[0] };
  const ant = `${fDM(R.R0 - rk.dias)} – ${fDM(R.R0 - 1)}`;
  const kpi = (rot, val, ayuda, small) => `<div class="kpi"${ayuda ? ` title="${esc(ayuda)}"` : ''}><span>${esc(rot)}</span>`
    + `<p>${val}${small ? `<small>${esc(small)}</small>` : ''}</p></div>`;
  const vVar = f.est ? `<i class="chip ${f.est}" title="${esc(f.ayuda)}">${f.est}</i>` : `<b class="${clsVar(f.var)}">${fmtVar(f.var)}</b>`;
  let vPpv;
  if (ci.ppv == null) vPpv = '<b class="igual">—</b>';
  else if (Math.abs(ci.ppv) < 1) vPpv = '<b class="igual">S/ 0</b>';
  else vPpv = `<b class="${ci.ppv > 0 ? 'sube' : 'baja'}">${ci.ppv > 0 ? '+' : '−'}S/ ${num(Math.abs(ci.ppv), 0)}</b>`;
  return kpi('Compra en el rango', `<b>${soles(ci.compra)}</b>`)
    + kpi(`vs. los ${rk.dias} días antes`, vVar, ant)
    + kpi('% del total', `<b>${(ci.compra / rk.totAll * 100).toFixed(1)}%</b>`)
    + kpi('Documentos · ticket', `<b>${num(ci.docs, 0)}</b>`, '', ci.docs ? soles(ci.compra / ci.docs) : '—')
    + kpi('vs. precio habitual', vPpv, 'Lo pagado de más (+) o de menos (−) contra el precio habitual de cada compra: '
      + 'la mediana de los 90 días anteriores, la misma de «Compras por período»');
}

// La curva: línea con área (o sin ella, en precio), el período en curso
// RAYADO con el tramo final punteado, el punto hueco y la raya de los
// mismos días del anterior (la `_fig_curva` de antes, sin Plotly).
function curvaSvg(F, C, ancho, alto) {
  const W = Math.max(280, ancho), PL = 46, PR = 12, PT = 8, PB = 22, PH = alto - PT - PB;
  const n = C.keys.length, slot = (W - PL - PR) / Math.max(1, n);
  const vals = C.ys.map((y) => (finito(y) ? y : null));
  const nums = vals.filter((x) => x != null);
  if (finito(C.ref)) nums.push(C.ref);
  if (!nums.length) nums.push(0);
  let y0, y1;
  if (C.medida === 'precio') {
    const lo = Math.min(...nums), hi = Math.max(...nums), pad = (hi - lo) * 0.2 || hi * 0.05 || 1;
    y0 = Math.max(0, lo - pad); y1 = hi + pad;
  } else { y0 = 0; y1 = Math.max(...nums) * 1.15 || 1; }
  const X = (i) => PL + (i + 0.5) * slot, Y = (v) => PT + PH - (v - y0) / (y1 - y0) * PH;
  const redondo = (r) => { const b = Math.pow(10, Math.floor(Math.log10(r || 1))); const f = r / b; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * b; };
  const fmtY = C.medida === 'precio' ? (v) => `S/ ${num(v, 1)}`
    : (v) => (v >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${+(v / 1e3).toFixed(1)}k` : String(+v.toFixed(1)));
  let svg = `<svg width="${W}" height="${alto}" viewBox="0 0 ${W} ${alto}" role="img" aria-label="Curva del proveedor">`
    + '<defs><pattern id="cpv-raya" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    + '<line x1="0" y1="0" x2="0" y2="7" class="rl"/></pattern></defs>';
  const paso = redondo((y1 - y0) / 4);
  for (let v = Math.ceil(y0 / paso) * paso; v <= y1 * 1.0001; v += paso) {
    svg += `<line class="gr" x1="${PL}" x2="${W - PR}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/>`
      + `<text class="ty" x="${PL - 6}" y="${(Y(v) + 3.5).toFixed(1)}" text-anchor="end">${fmtY(v)}</text>`;
  }
  const parc = !!C.parc && n > 0;
  if (parc) svg += `<rect class="raya" x="${(PL + (n - 1) * slot + slot * 0.05).toFixed(1)}" y="${PT}" width="${(slot * 0.9).toFixed(1)}" height="${PH}" fill="url(#cpv-raya)"/>`;
  const ult = parc && n > 1 ? n - 2 : n - 1;
  const pts = [];
  for (let i = 0; i <= ult; i += 1) if (vals[i] != null) pts.push([X(i), Y(vals[i])]);
  if (pts.length) {
    const linea = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
    if (C.medida !== 'precio') {
      svg += `<polygon class="area" points="${pts[0][0].toFixed(1)},${Y(y0).toFixed(1)} ${linea} ${pts[pts.length - 1][0].toFixed(1)},${Y(y0).toFixed(1)}"/>`;
    }
    svg += `<polyline class="ln" points="${linea}"/>`;
    pts.forEach(([x, y]) => { svg += `<circle class="pt" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3"/>`; });
  }
  if (parc && n > 1 && vals[n - 1] != null) {
    if (vals[n - 2] != null) svg += `<line class="lnp" x1="${X(n - 2).toFixed(1)}" y1="${Y(vals[n - 2]).toFixed(1)}" x2="${X(n - 1).toFixed(1)}" y2="${Y(vals[n - 1]).toFixed(1)}"/>`;
    if (finito(C.ref) && C.medida !== 'precio') svg += `<line class="ref" x1="${(X(n - 1) - 11).toFixed(1)}" x2="${(X(n - 1) + 11).toFixed(1)}" y1="${Y(C.ref).toFixed(1)}" y2="${Y(C.ref).toFixed(1)}"/>`;
    svg += `<circle class="pta" cx="${X(n - 1).toFixed(1)}" cy="${Y(vals[n - 1]).toFixed(1)}" r="4.5"/>`;
  }
  const etqs = C.keys.map((k) => etq(k, C.gran, true, F)), largo = Math.max(1, ...etqs.map((e) => e.length));
  // ~5,6 px por carácter a 11px (medido con «nov 25»: 34 px) y 8 de aire.
  const cada = Math.max(1, Math.ceil(n / Math.max(1, Math.floor((W - PL - PR) / (largo * 5.6 + 8)))));
  C.keys.forEach((k, i) => {
    if ((n - 1 - i) % cada === 0) svg += `<text class="tx" x="${X(i).toFixed(1)}" y="${alto - 6}" text-anchor="middle">${esc(etqs[i])}</text>`;
  });
  C.keys.forEach((k, i) => {
    svg += `<rect class="hit" data-acc="per-curva" data-v="${esc(k)}" x="${(PL + i * slot).toFixed(1)}" y="${PT}" width="${slot.toFixed(1)}" height="${PH}"></rect>`;
  });
  svg += '</svg>';
  return { svg, X, W };
}

function fmtMedida(v, medida, um) {
  if (!finito(v)) return '—';
  if (medida === 'cant') return cantTxt(v) + (um ? ` ${um}` : '');
  if (medida === 'precio') return precio(v);
  return soles(v);
}

// «Total del rango»: los productos comprados al proveedor en el rango. El
// producto en foco se despliega con sus proveedores de los últimos 90 días
// (precio promedio del período) y, abajo, los de todo el histórico.
function tablaProductos(F, R, X, colores) {
  const { p, ci, prod } = X;
  const g = new Map();
  ci.ls.forEach((l) => {
    const a = g.get(l.prod) || { prod: l.prod, valor: 0, cant: 0, ls: [] };
    a.valor += l.valor; a.cant += l.cant; a.ls.push(l);
    g.set(l.prod, a);
  });
  const rows = [...g.values()].sort((a, b) => b.valor - a.valor);
  if (!rows.length) return { n: 0, html: '<div class="nota-v">Sin productos para este proveedor.</div>' };
  const tot = suma(rows, (a) => a.valor) || 1, vmax = Math.max(1, ...rows.map((a) => a.valor));
  const filas = rows.map((a) => {
    const nom = F.prods[a.prod], um = moda(a.ls, F), hab = ci.hab.get(a.prod);
    let vh;
    if (!finito(hab)) vh = '<span class="var">—</span>';
    else if (Math.abs(hab) < 0.5) vh = '<span class="var igual" title="Igual al precio habitual (±0,5 %)">=</span>';
    else vh = `<span class="var ${hab > 0 ? 'sube' : 'baja'}">${fmtVar(hab)}</span>`;
    const foco = a.prod === prod;
    return `<div class="pl-f${foco ? ' foco' : ''}" data-acc="prod" data-v="${a.prod}" title="${esc(nom)} · clic: sus proveedores y su curva">`
      + celda(esc(nom), 'nm') + `<span class="vb"><span class="bar" style="width:${(a.valor / vmax * 62).toFixed(1)}%"></span>`
      + `<span class="v">${soles(a.valor)}</span></span>` + celda(`${Math.round(a.valor / tot * 100)}%`, 'r')
      + celda(cantTxt(a.cant) + (um ? ` ${esc(um)}` : ''), 'r') + celda(a.cant ? precio(a.valor / a.cant) : '—', 'r')
      + `<span class="r">${vh}</span><span class="ch">${foco ? '▴' : '▾'}</span></div>`
      + (foco ? `<div class="pl-provs">${provsDelProducto(F, R, a.prod, colores)}</div>` : '');
  });
  return { n: rows.length, html: '<div class="nota">El rango del ranking · clic en un producto: sus proveedores y su curva</div>'
    + tabla('pl', [celda('Producto'), celda('Valor', 'r'), celda('%', 'r'), celda('Cant.', 'r'), celda('P. prom.', 'r'),
      celda('vs. habitual', 'r', 'Contra la mediana del precio de los 90 días anteriores a cada compra'), celda('')],
    filas, [celda(`TOTAL · ${rows.length} ${rows.length === 1 ? 'producto' : 'productos'}`, 'nm'), celda(soles(suma(rows, (a) => a.valor)), 'r'),
      celda('100%', 'r'), celda(''), celda(''), celda(''), celda('')]) };
}
function provsDelProducto(F, R, i, colores) {
  const L = delProducto(F, i);
  // Los últimos 90 días que terminan en el fin del rango, con el precio
  // promedio del período (lo pagado ÷ lo comprado), del más barato al más caro.
  const g9 = new Map();
  const L90 = L.filter((l) => l.d > R.R1 - 90 && l.d <= R.R1 && l.cant > 0);
  L90.forEach((l) => {
    const a = g9.get(l.p) || { p: l.p, v: 0, c: 0, ult: l.d };
    a.v += l.valor; a.c += l.cant; a.ult = Math.max(a.ult, l.d);
    g9.set(l.p, a);
  });
  const r9 = [...g9.values()].filter((a) => a.c > 0).map((a) => ({ ...a, pr: a.v / a.c })).sort((a, b) => a.pr - b.pr || a.p - b.p);
  const pmin = r9.length ? r9[0].pr : null, um9 = moda(L90, F);
  let h = `<div class="sub">Últimos 90 días · ${r9.length} ${r9.length === 1 ? 'proveedor' : 'proveedores'} · precio promedio del período</div>`;
  h += r9.length ? r9.map((a) => {
    const dif = pmin ? (a.pr / pmin - 1) * 100 : 0;
    const marca = Math.abs(dif) < 0.05 ? '<i class="chip barato">más barato</i>' : `<span class="var sube">+${dif.toFixed(1)}%</span>`;
    return `<div class="p90">${celda(esc(F.noms[a.p]), 'nm', F.noms[a.p])}${celda(`${precio(a.pr)} ${marca}`, 'r')}`
      + `${celda(cantTxt(a.c) + (um9 ? ` ${esc(um9)}` : ''), 'r')}${celda(fDMA(a.ult), 'r f')}</div>`;
  }).join('') : '<div class="nota-v">Sin compras en los últimos 90 días.</div>';
  // Todo el histórico: el último precio de cada proveedor y su fecha; al
  // desplegarlo, la cantidad y el total.
  const gt = new Map();
  L.forEach((l) => {
    const a = gt.get(l.p) || { p: l.p, total: 0, cant: 0, ult: null, ls: [] };
    a.total += l.valor; a.cant += l.cant; a.ls.push(l);
    if (!a.ult || l.d >= a.ult.d) a.ult = l;
    gt.set(l.p, a);
  });
  const rt = [...gt.values()].sort((a, b) => b.total - a.total || a.p - b.p);
  rt.forEach((a) => { a.pu = a.ult && a.ult.cant ? a.ult.valor / a.ult.cant : null; });
  const ps = rt.map((a) => a.pu).filter(finito), pm = ps.length ? Math.min(...ps) : null;
  const tope = Math.max(1, ...rt.map((a) => a.total));
  const kAb = `hist|${i}`;
  h += `<details class="todo" data-k="${kAb}"${G.st.abiertos.has(kAb) ? ' open' : ''}><summary>Todo el histórico · ${rt.length} `
    + `${rt.length === 1 ? 'proveedor' : 'proveedores'} · último precio</summary><div class="pb">`
    + rt.map((a) => {
      const min = finito(a.pu) && a.pu === pm, um = moda(a.ls, F), ci = colores.get(a.p);
      return `<div class="pb-f${min ? ' min' : ''}"><span class="peso" style="width:${(a.total / tope * 100).toFixed(1)}%"></span>`
        + `<span class="sw" style="background:${color(ci)}"></span>${celda(esc(F.noms[a.p]), 'nm', F.noms[a.p])}`
        + `${celda(precio(a.pu), `r${min ? ' pmin' : ''}`)}${celda(a.ult ? fDMA(a.ult.d) : '—', 'r f')}`
        + `${celda(cantTxt(a.cant) + (um ? ` ${esc(um)}` : ''), 'r f')}${celda(sk(a.total), 'r')}</div>`;
    }).join('') + '</div></details>';
  return h;
}

function tabla(tipo, cab, filas, tot) {
  return `<div class="ft ${tipo}"><div class="ft-f ft-h">${cab.join('')}</div><div class="ft-l">${filas.join('')}</div>`
    + (tot ? `<div class="ft-f ft-t">${tot.join('')}</div>` : '') + '</div>';
}

function tablaDesglose(F, X) {
  const { C, prod } = X;
  const D = desglose(F, C, F.P[X.p], G.st.medida);
  if (!D.vis.length) return '<div class="nota-v">La curva no tiene períodos que desglosar.</div>';
  if (!D.filas.length) return '<div class="nota-v">Sin compras a este proveedor en los últimos períodos de la curva.</div>';
  const nv = D.vis.length, desde = D.tend.length - nv, medida = D.medida;
  const dec = medida === 'precio' ? 2 : medida === 'cant' ? 1 : 0;
  const txt = (v) => (!finito(v) || v === 0 ? '—' : num(v, dec));
  const parc = !!C.parc;
  const delta = (serie, a, total) => {
    const u = serie[serie.length - 1];
    if (D.modo === 'nada') return '<span class="r var">—</span>';
    if (D.modo === 'ref') {
      const rv = total ? (medida === 'valor' ? suma([...D.refV.values()], (x) => x) : null)
        : (medida === 'valor' ? D.refV.get(a.prod) : D.refC.get(a.prod));
      return `<span class="r">${filaVar(varPct(u, rv))}</span>`;
    }
    return `<span class="r">${filaVar(varPct(u, serie.length > 1 ? serie[serie.length - 2] : null))}</span>`;
  };
  const spark = (vals) => {
    const n = vals.length, nums = vals.filter((v) => finito(v));
    if (n < 2 || !nums.length) return '<span class="sp"></span>';
    let lo = 0, hi = Math.max(...nums) || 1;
    if (medida === 'precio') { const mn = Math.min(...nums), pad = (hi - mn) * 0.15 || hi * 0.05 || 1; lo = Math.max(0, mn - pad); hi += pad; }
    const Xs = (i) => 2 + i * 96 / (n - 1), Ys = (v) => 28 - (v - lo) / ((hi - lo) || 1) * 25;
    const ult = parc ? n - 2 : n - 1;
    let d = '', pen = false;
    for (let i = 0; i <= ult; i += 1) {
      if (!finito(vals[i])) { pen = false; continue; }
      d += `${pen ? 'L' : 'M'}${Xs(i).toFixed(1)},${Ys(vals[i]).toFixed(1)} `; pen = true;
    }
    let dash = '';
    if (parc && finito(vals[n - 1]) && finito(vals[n - 2])) dash = `<path class="d" d="M${Xs(n - 2).toFixed(1)},${Ys(vals[n - 2]).toFixed(1)} L${Xs(n - 1).toFixed(1)},${Ys(vals[n - 1]).toFixed(1)}"/>`;
    const bx = Math.max(0, Xs(Math.max(0, n - nv)) - 3);
    return `<span class="sp"><svg viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><rect x="${bx.toFixed(1)}" y="0" width="100" height="30"/>`
      + `<path class="l" d="${d.trim()}"/>${dash}</svg></span>`;
  };
  const filas = D.filas.map((a) => {
    const serieT = a.m, serie = serieT.slice(desde);
    const llenos = (parc ? serie.slice(0, -1) : serie).map((v) => v || 0);
    const tope = Math.max(0, ...llenos) || 1;
    const celdas = serie.map((v, k) => {
      const esParc = parc && k === serie.length - 1;
      let cls = `c${esParc ? ' parc' : ''}${!v ? ' z' : ''}`, estilo = '';
      if (!esParc) {
        if (medida === 'precio') {
          const j = desde + k - 1, ch = varPct(v, j >= 0 ? serieT[j] : null);
          if (finito(ch) && ch > UMBRAL_PRECIO) cls += ' sube'; else if (finito(ch) && ch < -UMBRAL_PRECIO) cls += ' baja';
        } else if (v) estilo = ` style="--t:${Math.round(v / tope * 30)}%"`;
      }
      return `<span class="${cls}"${estilo}>${txt(v)}</span>`;
    }).join('');
    const nom = F.prods[a.prod];
    return `<div class="pm-f${a.prod === prod ? ' foco' : ''}" data-acc="prod-curva" data-v="${a.prod}" title="${esc(nom)} · clic: su curva">`
      + `<span class="nm">${esc(nom)}${a.um ? `<small>${esc(a.um)}</small>` : ''}</span>${spark(serieT)}${celdas}${delta(serie, a, false)}</div>`;
  });
  let tot = null;
  if (D.total) {
    tot = ['<span class="nm" title="Todos sus productos: los mismos números que la curva">Total</span>', '<span class="sp"></span>',
      ...D.total.map((v, k) => `<span class="c${parc && k === D.total.length - 1 ? ' parc' : ''}">${txt(v)}</span>`), delta(D.total, null, true)];
  }
  const head = D.vis.map((k, i) => (parc && i === nv - 1 ? C.parc.rot : etq(k, C.gran, false, F)));
  let titD = 'vs. anterior';
  if (D.modo === 'ref') titD = 'vs. ' + (C.gran === 'Semana' ? C.parc.rotRef.split(' de la ')[0] : C.parc.rotRef);
  const que = { valor: 'Soles', cant: 'Cantidad', precio: 'Precios' }[medida];
  const gr = { Día: 'día', Semana: 'semana', Mes: 'mes', Año: 'año', Documento: 'documento' }[C.gran];
  let nota = `<b>${que} por ${gr}</b> · los últimos ${nv} puntos de la curva`;
  if (parc) nota += medida === 'precio' ? ` · ${esc(C.parc.rot)} se compara con el período anterior entero` : ` · ${esc(C.parc.rot)} se compara con ${esc(C.parc.rotRef)}`;
  if (medida === 'precio') nota += ` · rojo: subió más de ${UMBRAL_PRECIO.toFixed(0)} % contra el anterior; verde: bajó`;
  if (D.modo === 'nada') nota += ` · entre un ${gr} y otro sólo se compara el precio`;
  nota += ' · clic en una fila: su curva';
  return `<div class="nota">${nota}</div><div class="ft pm" style="--n:${nv}"><div class="ft-f ft-h"><span>Producto</span>`
    + '<span class="sp" title="Los últimos puntos de la curva; la franja, las columnas de la tabla">Tendencia</span>'
    + head.map((h) => `<span class="r">${esc(h)}</span>`).join('') + `<span class="r">${esc(titD)}</span></div>`
    + `<div class="ft-l">${filas.join('')}</div>${tot ? `<div class="ft-f ft-t">${tot.join('')}</div>` : ''}</div>`;
}

function tablaDocumentos(F, X) {
  const { ci, p } = X;
  const ls = ci.ls.filter((l) => !l.sinDoc);
  if (!ls.length) return { n: 0, html: '<div class="nota-v">Sin números de documento para este proveedor en el rango.</div>' };
  const hd = historiaDocs(F.P[p]);
  const g = new Map();
  ls.forEach((l) => {
    const a = g.get(l.doc) || { doc: l.doc, fecha: l.d, valor: 0, prods: new Map() };
    a.fecha = Math.min(a.fecha, l.d); a.valor += l.valor;
    const b = a.prods.get(l.prod) || { prod: l.prod, cant: 0, valor: 0, um: l.um };
    b.cant += l.cant; b.valor += l.valor;
    a.prods.set(l.prod, b);
    g.set(l.doc, a);
  });
  const docs = [...g.values()].sort((a, b) => b.fecha - a.fecha || b.doc - a.doc);
  const filas = docs.map((a) => {
    const k = `doc|${a.doc}`, dias = hd.dias.get(a.doc), s = hd.top.get(a.doc);
    let subio = '<span class="var">—</span>';
    if (s) {
      const n = hd.nSube.get(a.doc) || 1;
      subio = `<span class="var sube">▲ ${s.dp.toFixed(1)}%</span> ${esc(F.prods[s.prod])}${n > 1 ? ` <small>y ${n - 1} más</small>` : ''}`;
    }
    const lin = [...a.prods.values()].sort((x, y) => y.valor - x.valor).map((b) => {
      const um = F.umsRaw[b.um] ? F.ums[b.um] : '';
      return `<div class="dl-l">${celda(esc(F.prods[b.prod]), 'nm', F.prods[b.prod])}${celda(cantTxt(b.cant) + (um ? ` ${esc(um)}` : ''), 'r')}`
        + `${celda(b.cant ? precio(b.valor / b.cant) : '—', 'r')}${celda(soles(b.valor), 'r')}</div>`;
    }).join('');
    return `<details class="dl" data-k="${k}"${G.st.abiertos.has(k) ? ' open' : ''}><summary class="ft-f">`
      + `${celda(fDMA(a.fecha))}${celda(esc(F.docs[a.doc]), 'nm')}${celda(String(a.prods.size), 'r')}${celda(soles(a.valor), 'r')}`
      + `${celda(dias == null ? '—' : String(dias), 'r')}<span class="nm" title="${s ? esc(F.prods[s.prod]) : ''}">${subio}</span>`
      + '<span class="ch">▾</span></summary><div class="dl-d"><div class="dl-l enc"><span>Producto</span><span class="r">Cant.</span>'
      + `<span class="r">P. unit.</span><span class="r">Valor</span></div>${lin}</div></details>`;
  });
  const tot = suma(docs, (a) => a.valor);
  return { n: docs.length, html: '<div class="nota">El rango del ranking · Días: desde la compra anterior · Subió de precio: contra la '
    + 'compra anterior del mismo producto a este proveedor</div>'
    + tabla('dd', [celda('Fecha'), celda('Documento'), celda('Prods', 'r', 'Productos distintos en el documento'), celda('Valor', 'r'),
      celda('Días', 'r'), celda('Subió de precio'), celda('')], filas,
    [celda(`Total · ${num(docs.length, 0)} ${docs.length === 1 ? 'documento' : 'documentos'} · ticket ${soles(tot / docs.length)}`, 'nm tot3'),
      celda(soles(tot), 'r'), celda(''), celda(''), celda('')]) };
}

function tablaDocsPeriodo(F, X) {
  const { C, p } = X;
  const idx = new Map(C.keys.map((k, i) => [k, i]));
  const vals = C.keys.map(() => 0), nDocs = C.keys.map(() => new Set()), porPer = C.keys.map(() => new Map());
  C.deP.forEach((l) => {
    const i = idx.get(l.k);
    if (i == null) return;
    vals[i] += l.valor;
    if (l.sinDoc) return;
    nDocs[i].add(l.doc);
    const a = porPer[i].get(l.doc) || { doc: l.doc, fecha: l.d, valor: 0, filas: 0 };
    a.fecha = Math.min(a.fecha, l.d); a.valor += l.valor; a.filas += 1;
    porPer[i].set(l.doc, a);
  });
  let refDocs = null;
  if (C.parc) refDocs = suma(F.P[p].filter((l) => l.d >= C.parc.refIni && l.d <= C.parc.refFin), (l) => l.valor);
  const filas = [];
  for (let i = C.keys.length - 1; i >= 0; i -= 1) {
    const k = C.keys[i], esParc = C.parc && i === C.keys.length - 1;
    const v = esParc ? varPct(vals[i], refDocs) : varPct(vals[i], i ? vals[i - 1] : null);
    const rot = esParc ? C.parc.rot : etq(k, C.gran, false, F);
    const ds = [...porPer[i].values()].sort((a, b) => b.fecha - a.fecha || b.doc - a.doc);
    const kk = `per|${C.gran}|${k}`;
    filas.push(`<details class="dl" data-k="${esc(kk)}"${G.st.abiertos.has(kk) ? ' open' : ''}><summary class="ft-f">`
      + `<span class="nm${esParc ? ' parc' : ''}"><b>${esc(rot)}</b></span>${celda(String(nDocs[i].size), 'r')}${celda(soles(vals[i]), 'r')}`
      + `<span class="r">${filaVar(v)}</span><span class="ch">▾</span></summary><div class="dl-d">`
      + (ds.length ? '<div class="dl-l per enc"><span>Fecha</span><span>Documento</span><span class="r">Filas</span><span class="r">Total</span></div>'
        + ds.map((a) => `<div class="dl-l per">${celda(fDMA(a.fecha))}${celda(esc(F.docs[a.doc]), 'nm')}${celda(String(a.filas), 'r')}${celda(soles(a.valor), 'r')}</div>`).join('')
        : '<div class="nota-v">Sin documentos en el período.</div>') + '</div></details>');
  }
  let nota = 'Los períodos de la curva · Var. %: contra el período anterior';
  if (C.parc) nota += ` · ${esc(C.parc.rot)} contra ${esc(C.parc.rotRef)}`;
  const nd = suma(nDocs, (s) => s.size), tv = suma(vals, (x) => x);
  return `<div class="nota">${nota}</div>` + tabla('dp', [celda('Período'), celda('Docs', 'r'), celda('Valor', 'r'), celda('Var. %', 'r'), celda('')],
    filas, [celda(`Total · ${num(nd, 0)} ${nd === 1 ? 'documento' : 'documentos'}`, 'nm'), celda(''), celda(soles(tv), 'r'), celda(''), celda('')]);
}

function ficha() {
  const { F, R, st } = G, X = G.X;
  if (X.p == null) return '<div class="nota-v">Sin proveedores en el rango.</div>';
  const { p, prod, ci, C } = X;
  const nom = F.noms[p], H = F.P[p];
  const desde = H.length ? H[0].d : null;
  const colores = new Map(X.rk.top.map((q, i) => [q, i]));
  // Cabecera: nombre, «desde», la ventana de la curva y, con «Rango», su tamaño.
  const opRot = OPS.find((o) => o[0] === st.op)[1];
  let ven = `<div class="men"><button class="men-b" data-acc="menu" data-v="op" aria-haspopup="listbox">${esc(opRot)} <i>▾</i></button>`
    + (st.menu === 'op' ? `<div class="men-l" role="listbox">${OPS.map(([k, t]) => `<button role="option" class="${k === st.op ? 'on' : ''}" data-acc="op" data-v="${k}">${esc(t)}</button>`).join('')}</div>` : '')
    + '</div>';
  if (C.win) {
    const w = C.win;
    const fmtW = (o) => (o == null ? `Auto ${VENTANA_AUTO}` : o === w.nPer ? (w.nPer < 100 ? `Todo ${w.nPer}` : 'Todo') : String(o));
    ven += `<div class="men"><button class="men-b" data-acc="menu" data-v="win" title="Períodos visibles">${esc(fmtW(w.tam))} <i>▾</i></button>`
      + (st.menu === 'win' ? `<div class="men-l">${w.ops.map((o) => `<button class="${o === w.tam ? 'on' : ''}" data-acc="win" data-v="${o == null ? '' : o}">${esc(fmtW(o))}</button>`).join('')}</div>` : '')
      + '</div>'
      + `<button class="fl" data-acc="mover" data-v="-1" title="Períodos anteriores"${w.ini <= 0 ? ' disabled' : ''}>‹</button>`
      + `<button class="fl" data-acc="mover" data-v="1" title="Períodos siguientes"${w.ini >= w.iniMax ? ' disabled' : ''}>›</button>`;
  }
  const cab = `<div class="cab"><h3 title="${esc(nom)}">${esc(nom)}${desde != null ? `<span>desde ${mesAnio(desde)}</span>` : ''}</h3>${ven}</div>`;
  // La curva y sus controles.
  const sujeto = prod != null ? `<b>${esc(trunc(F.prods[prod], 30))}</b> · ${esc(trunc(nom, 22))}` : `<b>${esc(trunc(nom, 30))}</b> · todo lo comprado`;
  const ctrl = `<div class="cc"><span class="tit" title="${esc(prod != null ? F.prods[prod] + ' · ' + nom : nom)}">Curva de ${sujeto}</span>`
    + (prod != null ? '<button class="x" data-acc="soltar" title="Volver a todo el proveedor">✕</button>' : '')
    + `<span class="esp"></span><div class="seg">${MEDIDAS.map(([k, t]) => `<button class="${k === st.medida ? 'on' : ''}" data-acc="medida" data-v="${k}">${t}</button>`).join('')}</div>`
    + `<div class="seg">${GRANOS.map(([k, t]) => `<button class="${k === st.gran ? 'on' : ''}" data-acc="gran" data-v="${k}">${t}</button>`).join('')}</div></div>`;
  let curva;
  if (C.keys.length) {
    const ancho = (G.raices.ficha && G.raices.ficha.clientWidth) || 700;
    const c = curvaSvg(F, C, ancho, F.alto);
    G.cX = c.X; G.cW = c.W;
    curva = `<div class="curva" style="height:${F.alto}px">${c.svg}<div class="tip" hidden></div></div>`;
  } else curva = `<div class="sin-curva" style="height:${F.alto}px">Sin compras de este proveedor en la ventana.</div>`;
  const ley = [], n = C.keys.length;
  if (C.parc && n) {
    ley.push(`<span><i class="m hueco"></i>${esc(C.parc.rot)} en curso: ${esc(fmtMedida(C.ys[n - 1], C.medida, C.um))}</span>`);
    if (C.medida === 'precio') ley.push(`<span>contra el período anterior entero: ${filaVar(varPct(C.ys[n - 1], n > 1 ? C.ys[n - 2] : null))}</span>`);
    else ley.push(`<span><i class="m raya"></i>${esc(C.parc.rotRef)}: ${esc(fmtMedida(C.ref, C.medida, C.um))} ${filaVar(varPct(C.ys[n - 1], C.ref))}</span>`);
  }
  if (st.medida !== 'valor' && prod == null) ley.push('<span>en soles: la cantidad y el precio van por producto (clic en uno)</span>');
  if (C.hist) ley.push(`<span>${esc({ '3m': 'últimos 3 meses', '12m': 'últimos 12 meses', '24m': 'últimos 24 meses', Todo: 'todo el histórico' }[st.op])}</span>`);
  // Las pestañas.
  const nProd = new Set(ci.ls.map((l) => l.prod)).size;
  const tabs = [['prod', `Productos · ${nProd}`], ['doc', `Documentos · ${ci.docs}`]]
    .map(([k, t]) => `<button class="tab${k === st.tab ? ' on' : ''}" data-acc="tab" data-v="${k}">${esc(t)}</button>`).join('');
  let modos;
  if (st.tab === 'prod') modos = [['tot', 'Total del rango'], ['per', 'Desglose']].map(([k, t]) => `<button class="pw${k === st.pmodo ? ' on' : ''}" data-acc="pmodo" data-v="${k}">${t}</button>`).join('');
  else if (C.gran === 'Documento') modos = '';
  else modos = [['doc', 'Por documento'], ['per', GRAN_POR[C.gran]]].map(([k, t]) => `<button class="pw${k === st.dmodo ? ' on' : ''}" data-acc="dmodo" data-v="${k}">${t}</button>`).join('');
  let cuerpo;
  if (st.tab === 'prod' && st.pmodo === 'per') cuerpo = tablaDesglose(F, X);
  else if (st.tab === 'prod') cuerpo = tablaProductos(F, R, X, colores).html;
  else if (st.dmodo === 'per' && C.gran !== 'Documento') cuerpo = tablaDocsPeriodo(F, X);
  else cuerpo = tablaDocumentos(F, X).html;
  return cab + `<div class="kpis">${kpis(F, R, X)}</div>` + ctrl + curva
    + (ley.length ? `<div class="ley">${ley.join('')}</div>` : '')
    + `<div class="tabs">${tabs}<span class="esp"></span>${modos}</div><div class="cuerpo">${cuerpo}</div>`;
}

function pintarFicha() {
  const raiz = G.raices.ficha;
  if (!raiz) return;
  const scroll = raiz.querySelector('.ft-l');
  const y = scroll ? scroll.scrollTop : 0;
  const de = `${G.X.p}|${G.st.tab}|${G.st.pmodo}|${G.st.dmodo}`;
  const mismo = G.fichaDe === de;
  raiz.innerHTML = ficha();
  G.fichaDe = de;
  const nuevo = raiz.querySelector('.ft-l');
  if (nuevo && mismo) nuevo.scrollTop = y;
  const foco = raiz.querySelector('.pl-f.foco');
  if (foco && G.scrollAlFoco) { foco.scrollIntoView({ block: 'nearest' }); G.scrollAlFoco = false; }
}

// La ficha al pasar el cursor por un período (el hover de la curva de antes).
function pintarTip(k) {
  const raiz = G.raices.ficha;
  const tip = raiz && raiz.querySelector('.tip');
  const C = G.X && G.X.C;
  if (!tip || !C) return;
  const i = k == null ? -1 : C.keys.indexOf(k);
  if (i < 0) { tip.hidden = true; return; }
  const n = C.keys.length, esParc = C.parc && i === n - 1;
  const rot = esParc ? C.parc.rot : (C.gran === 'Mes' ? mesAnio(dn(`${k}-01`)) : etq(k, C.gran, false, G.F));
  const cmp = esParc && C.medida !== 'precio' ? varPct(C.ys[i], C.ref) : varPct(C.ys[i], i ? C.ys[i - 1] : null);
  let html = `<b>${esc(rot)}</b><div class="v">${esc(fmtMedida(C.ys[i], C.medida, C.um))}</div><div>vs. anterior: ${fmtVar(cmp)}</div>`;
  if (C.medida === 'valor' && C.gran !== 'Documento') html += `<div>${(C.v[i] / (C.tot[i] || 1) * 100).toFixed(1)}% del total</div>`;
  html += `<div>${C.docs[i]} documentos</div><div class="tm">clic: sus documentos</div>`;
  tip.innerHTML = html;
  tip.hidden = false;
  const tw = tip.offsetWidth || 190, x = G.cX(i);
  tip.style.left = `${x + 14 + tw <= G.cW ? x + 14 : Math.max(0, x - 14 - tw)}px`;
}

function pintar() {
  const { R, F } = G;
  if (!R || !F || R.sello !== F.sello) {
    if (G.raices.ficha && !G.raices.ficha.innerHTML) G.raices.ficha.innerHTML = '<div class="nota-v">Cargando…</div>';
    return;
  }
  G.X = calcular(F, R, G.st);
  pintarRank();
  pintarFicha();
}

// ── Los clics ────────────────────────────────────────────────────────────
function accion(acc, val) {
  const st = G.st;
  if (acc !== 'menu') st.menu = null;
  if (acc === 'orden') {
    const s = st.sort, d0 = val === 'nom' ? 1 : -1;
    st.sort = !s || s.col !== val ? { col: val, dir: d0 } : s.dir === d0 ? { col: val, dir: -s.dir } : null;
  } else if (acc === 'fila') {
    const p = +val;
    st.foco = st.foco === p ? null : p;
    st.prod = null;
  } else if (acc === 'excel') { excelRank(); return; }
  else if (acc === 'menu') { st.menu = st.menu === val ? null : val; pintarFicha(); return; }
  else if (acc === 'op') st.op = val;
  else if (acc === 'win') { st.win = val === '' ? null : +val; }
  else if (acc === 'mover') { const w = G.X.C.win; if (w) st.winIni = Math.min(Math.max(0, w.ini + (+val) * w.ven), w.iniMax); }
  else if (acc === 'medida') st.medida = val;
  else if (acc === 'gran') st.gran = val;
  else if (acc === 'tab') st.tab = val;
  else if (acc === 'pmodo') st.pmodo = val;
  else if (acc === 'dmodo') st.dmodo = val;
  else if (acc === 'prod') { const i = +val; st.prod = st.prod === i ? null : i; }
  else if (acc === 'prod-curva') { const i = +val; st.prod = st.prod === i ? null : i; }
  else if (acc === 'soltar') st.prod = null;
  else if (acc === 'per-curva') {
    // El clic en un período de la curva abre sus documentos.
    st.tab = 'doc';
    const C = G.X.C;
    if (C.gran === 'Documento') { const k = `doc|${+val.split('|')[1]}`; st.dmodo = 'doc'; st.abiertos.add(k); }
    else { st.dmodo = 'per'; st.abiertos.add(`per|${C.gran}|${val}`); }
  } else return;
  pintar();
}
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.disabled) {
      if (G.st.menu && !(ev.target.closest && ev.target.closest('.men'))) { G.st.menu = null; pintarFicha(); }
      return;
    }
    accion(b.dataset.acc, b.dataset.v);
  });
  // Lo desplegado se recuerda: la ficha se vuelve a dibujar con cada clic.
  raiz.addEventListener('toggle', (ev) => {
    const d = ev.target;
    if (!d || !d.dataset || !d.dataset.k) return;
    if (d.open) G.st.abiertos.add(d.dataset.k); else G.st.abiertos.delete(d.dataset.k);
  }, true);
  raiz.addEventListener('mouseover', (ev) => {
    const b = ev.target.closest('[data-acc="per-curva"]');
    if (b && raiz.contains(b)) pintarTip(b.dataset.v);
  });
  raiz.addEventListener('mouseout', (ev) => {
    const b = ev.target.closest('[data-acc="per-curva"]');
    if (b && !(ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest('[data-acc="per-curva"]'))) pintarTip(null);
  });
  raiz.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && G.st.menu) { G.st.menu = null; pintarFicha(); }
  });
}

const ESQ_RANK = '<div class="tabla"></div><p class="pie"><span></span>'
  + '<button class="excel" data-acc="excel" title="Baja el ranking tal como se ve">Excel</button></p>';

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.parte) return;
  if (data.parte === 'ficha') {
    let raiz = parentElement.querySelector('.cpvf');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'cpvf';
      parentElement.appendChild(raiz);
      enlazar(raiz);
      // Al cambiar de ancho, la curva se vuelve a dibujar a su medida.
      let ancho = 0, espera = 0;
      new ResizeObserver(() => {
        if (Math.abs(raiz.clientWidth - ancho) < 2) return;
        ancho = raiz.clientWidth;
        clearTimeout(espera);
        espera = setTimeout(() => { if (G.R && G.F && G.R.sello === G.F.sello && G.X) pintarFicha(); }, 120);
      }).observe(raiz);
    }
    G.raices.ficha = raiz;
    if (!G.F || G.F.sello !== data.sello) G.F = leerFicha(data);
  } else {
    let raiz = parentElement.querySelector('.cpvr');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'cpvr';
      raiz.innerHTML = ESQ_RANK;
      parentElement.appendChild(raiz);
      enlazar(raiz);
    }
    G.raices.rank = raiz;
    if (G.rankData !== data) { G.rankData = data; G.R = leerRank(data); }
  }
  pintar();
}
