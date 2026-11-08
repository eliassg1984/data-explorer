// Compras › Proveedor (reglas #715 y #774).
//
// La monta graficos/compras/proveedor.py con st.components.v2 (sin iframe,
// estilos en un shadow root) DOS VECES: `parte: "ficha"` trae el historial de
// líneas y no dibuja nada; `parte: "rank"` trae el rango y el filtro, y dibuja
// la pantalla. Así cambiar la fecha no vuelve a mandar el historial.
// `_xlsx.js` y `lista_ficha.js` van antepuestos.
//
// `window.__cpProv` guarda los datos de los dos montajes y lo elegido: sobrevive
// a que Streamlit vuelva a montar la pieza. A Python vuelven sólo la fecha y el
// filtro de proveedores (widgets suyos, en el hueco de la cabecera) y el menú de
// familias, que es el filtro de la página.
//
// Las cuentas son las de la vista de antes (regla #646): `_contra_anterior`
// y `_estado` del ranking, `_ppv`, la curva con `periodo.ventana`,
// `inicio_de_periodo` y `tramo_parcial`, `_html_desglose`, `_historia_docs`.
// Lo vigila test_proveedor_pieza.py, que corre `calcular` en Chromium contra
// las mismas cuentas en pandas.

const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIA = 864e5;
// Una línea del historial (proveedor.historial_pieza).
const RL = { dia: 0, prod: 1, doc: 2, cant: 3, valor: 4, ref: 5, um: 6, flag: 7 };
const GRANOS = [['Día', 'Día'], ['Semana', 'Semana'], ['Mes', 'Mes'], ['Año', 'Año'], ['Documento', 'Documento']];
const GRAN_POR = { Día: 'Por día', Semana: 'Por semana', Mes: 'Por mes', Año: 'Por año', Documento: 'Por documento' };
const MEDIDAS = [['valor', 'Soles'], ['cant', 'Cantidad'], ['precio', 'Precio']];
const MEDIDAS_PRODUCTOS = [['valor', 'Valor comprado (S/)'], ['cant', 'Cantidad'], ['precio', 'Precio unitario'], ['ambos', 'Cantidad y precio'], ['tres', 'Cantidad, precio y valor']];
const OPS = [['Rango', 'el rango'], ['3m', '3 meses'], ['12m', '12 meses'], ['24m', '24 meses'], ['Todo', 'todo']];
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
const fmtVar = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.05 ? '0 %' : `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(1)} %`);
const solesG = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.5 ? 'S/ 0' : `${v > 0 ? '+' : '−'}S/ ${num(Math.abs(v), 0)}`);
const colorPpv = (v) => (!finito(v) || Math.abs(v) < 1 ? '' : v > 0 ? 'rojo' : 'verde');
const coincide = (nom, q) => sinTildes(q).split(/\s+/).filter(Boolean).every((p) => sinTildes(nom).includes(p));
const tramo = (a, b) => { const x = ymd(a), y = ymd(b); return x[1] === y[1] ? `${x[2]}–${y[2]} ${MES[y[1] - 1]}` : `${fCorta(a)} – ${fCorta(b)}`; };
// Rojo si subió el gasto, verde si bajó; sin color por debajo del 0,5 %.
const clsVar = (v) => (!finito(v) || Math.abs(v) < 0.5 ? '' : v > 0 ? 'sube' : 'baja');
const filaVar = (v, conColor) => `<span class="var ${conColor ? clsVar(v) : 'igual'}">${fmtVar(v)}</span>`;
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

// El precio de compra es el ponderado. Un mismo producto con unidades
// distintas no tiene una cantidad ni un precio unitario que se puedan juntar.
function medidasDe(ls, F) {
  const unidades = new Set(ls.map((l) => F.ums[l.um] || ''));
  const mezcla = unidades.size > 1, valor = suma(ls, (l) => l.valor);
  const cant = mezcla ? null : suma(ls, (l) => l.cant);
  return { valor, cant, precio: cant > 0 ? valor / cant : null, um: mezcla ? '' : [...unidades][0] || '', mezcla };
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
    ref: l[RL.ref], um: l[RL.um], flag: l[RL.flag] || 0, sinDoc: !data.docs[l[RL.doc]] })));
  const todas = P.flat();
  let min = Infinity;
  todas.forEach((l) => { if (l.d < min) min = l.d; });
  return { sello: data.sello, ULT: dn(data.ultimo), MIN: min, provs: data.provs, noms: data.noms, prods: data.prods,
    docs: data.docs, ums: data.ums, umsRaw: data.ums.map((u) => !vacio.has(u)), P, todas,
    porProd: null };
}
function leerRank(data) {
  return { sello: data.sello, R0: dn(data.rango[0]), R1: dn(data.rango[1]), sel: data.sel || [], otros: !!data.otros, pagina: data.pagina || null };
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
  // A quienes se les compró en el período anterior y en este no. Sin ellos, el
  // total de «Vs. antes» no da lo mismo que el de Producto (regla #774).
  const yaNo = [];
  if (!fuera.length) for (let p = 0; p < n; p += 1) if (!hay[p] && prev[p] > 0) yaNo.push({ p, valor: 0, pct: 0, prev: prev[p], var: -100, est: '', ayuda: '', ya: true });
  if (R.otros && fuera.length) {
    const v = suma(fuera, (p) => val[p]);
    filas.push({ p: -1, valor: v, pct: v / totAll * 100, prev: suma(fuera, (p) => prev[p]), var: null, est: '', ayuda: '', otros: fuera.length });
  }
  const vTot = suma(filas, (f) => f.valor);
  const vals = filas.map((f) => f.valor).sort((a, b) => b - a);
  let acum = 0, n80 = 0;
  vals.forEach((v) => { acum += v; if (acum / totAll * 100 < 80) n80 += 1; });
  return { filas, defecto, top, totAll, dias, yaNo, n80: vals.length ? n80 + 1 : 0,
    total: { n: filas.length, valor: vTot, pct: suma(filas, (f) => f.pct), var: varPct(vTot, suma(filas, (f) => f.prev) + suma(yaNo, (f) => f.prev)) } };
}

// Una línea que entra en un precio: con habitual, cantidad y valor, y sin marca.
// Hasta la regla #774 las marcadas entraban acá y no en Precios ni en Producto:
// Anhelar daba +S/ 377 donde era +S/ 137, y The Spirit cambiaba de signo.
const vale = (l) => finito(l.ref) && l.cant > 0 && l.valor > 0 && !l.flag;

// Las cifras del rango de un proveedor y el «vs. precio habitual» (`_ppv`):
// (precio pagado − habitual) × cantidad, y el % por producto.
function cifras(F, R, p) {
  const ls = F.P[p].filter((l) => l.d >= R.R0 && l.d <= R.R1);
  const compra = suma(ls, (l) => l.valor);
  const docs = new Set(ls.filter((l) => !l.sinDoc).map((l) => l.doc)).size;
  let ppv = 0, hay = false;
  const porProd = new Map();
  ls.forEach((l) => {
    if (!vale(l)) return;
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

// Lo que dicen los indicadores y la lista, por proveedor: el efecto del precio, sus
// documentos y productos, y lo que en 90 días sólo se le compró a él.
function panorama(F, R) {
  const pv90 = new Map();
  F.todas.forEach((l) => {
    if (l.d <= R.R1 - 90 || l.d > R.R1) return;
    if (!pv90.has(l.prod)) pv90.set(l.prod, new Set());
    pv90.get(l.prod).add(l.p);
  });
  const det = new Map();
  F.todas.forEach((l) => {
    if (l.d < R.R0 || l.d > R.R1) return;
    if (!det.has(l.p)) det.set(l.p, { ppv: 0, hay: false, docs: new Set(), prods: new Set(), nfl: 0, solos: new Set(), vSolo: 0, ult: null });
    const a = det.get(l.p);
    a.prods.add(l.prod);
    if (!l.sinDoc) a.docs.add(l.doc);
    if (l.flag) a.nfl += 1;
    if (vale(l)) { a.ppv += l.valor - l.ref * l.cant; a.hay = true; }
    if (pv90.get(l.prod) && pv90.get(l.prod).size === 1) { a.solos.add(l.prod); a.vSolo += l.valor; }
    a.ult = a.ult == null ? l.d : Math.max(a.ult, l.d);
  });
  return { pv90, det };
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
  const p = st.foco != null && F.P[st.foco] && (F.P[st.foco].some((l) => l.d >= R.R0 && l.d <= R.R1) || rk.yaNo.some((f) => f.p === st.foco)) ? st.foco : rk.defecto;
  if (p == null) return { rk };
  const ci = cifras(F, R, p);
  const prods = new Set(ci.ls.map((l) => l.prod));
  const prod = st.prod != null && prods.has(st.prod) ? st.prod : null;
  const C = curvaDe(F, R, st, p, prod);
  return { rk, p, prod, ci, C };
}

window.__cpProvCalc = { leerFicha, leerRank, ranking, cifras, panorama, curvaDe, desglose, historiaDocs, calcular, clave, parcial, medidasDe };

const G = window.__cpProv || (window.__cpProv = {
  st: { gran: 'Día', op: 'Rango', medida: 'valor', tab: 'curva', pmodo: 'per', pmedida: 'ambos', dmodo: 'doc', kpi: 'todos', ver: 'todos', q: '', foco: null, per: null, amp: null, menu: null, abiertos: new Set() },
  R: null, F: null });

if (G.st.det == null) G.st.det = !!lfLeer('cp_prov_det', false);
if (!G.st.pleg) G.st.pleg = lfLeer('cp_prov_pleg', {});

function comoHtml(R) {
  const rk = G.X.rk, ant = tramo(R.R0 - rk.dias, R.R0 - 1);
  return `<p>Lo comprado del ${fCorta(R.R0)} al ${fCorta(R.R1)}, sin IGV, contra los mismos ${rk.dias} días anteriores (${esc(ant)}).</p><dl>`
    + '<dt>Proveedores</dt><dd>A quienes se les compró en el rango; «hacen el 80 %», los que suman el 80 % de lo comprado.</dd>'
    + '<dt>Subieron, bajaron</dt><dd>Lo pagado de más o de menos contra el precio habitual de cada compra: la mediana de los 90 días anteriores de ese producto. Sin las compras para revisar: es la misma cuenta de Precios.</dd>'
    + '<dt>Sólo a uno</dt><dd>Productos que en los últimos 90 días tuvieron un solo proveedor: si falla, no hay otro a la mano.</dd>'
    + '<dt>Vs. antes</dt><dd>En soles y en gris: comprar más o menos no es bueno ni malo. El total cuenta a quienes ya no se les compró.</dd>'
    + '<dt>Precio</dt><dd>El efecto del precio del proveedor, en rojo si pagaste de más.</dd>'
    + '<dt>Ticket, Cada</dt><dd>Compra ÷ documentos, y días del rango ÷ documentos. Con «Detalle».</dd></dl><p>Es un cálculo propio, no un estándar.</p>';
}

function excelRank() {
  const { F, R } = G, V = G.V, rk = G.X.rk;
  const filas = V.vis.map((f) => {
    const d = V.det(f), nd = d.docs ? d.docs.size : 0;
    return [f.p < 0 ? `Otros (${f.otros})` : F.noms[f.p], f.valor, f.prev, f.var, f.est || (f.ya ? 'ya no' : ''), f.pct, d.hay ? d.ppv : null, d.prods ? d.prods.size : null, nd, nd ? f.valor / nd : null, d.solos.size, d.ult != null ? iso(d.ult) : ''];
  });
  bajar(`compras_proveedores_${iso(R.R0)}_${iso(R.R1)}.xlsx`, libro([{ nombre: 'Proveedores',
    cabeza: ['Proveedor', 'Valor (S/)', `Período anterior (${rk.dias} días antes, S/)`, 'Δ % vs. período anterior', 'Estado', '% del total', 'Efecto del precio (S/)', 'Productos', 'Documentos', 'Ticket (S/)', 'Productos que sólo se le compran a él', 'Última compra'], filas }]));
}

// ── La ficha ─────────────────────────────────────────────────────────────
const celda = (t, cls, ayuda) => `<span class="${cls || ''}"${ayuda ? ` title="${esc(ayuda)}"` : ''}>${t}</span>`;
const etqLarga = (k, C, F) => (C.gran === 'Mes' ? mesAnio(dn(`${k}-01`)) : etq(k, C.gran, false, F));

function fmtMedida(v, medida, um) {
  if (!finito(v)) return '—';
  if (medida === 'cant') return cantTxt(v) + (um ? ` ${um}` : '');
  if (medida === 'precio') return precio(v);
  return soles(v);
}

const medidaProductos = () => MEDIDAS_PRODUCTOS.some(([k]) => k === G.st.pmedida) ? G.st.pmedida : 'ambos';
const tituloMedidaProductos = () => MEDIDAS_PRODUCTOS.find(([k]) => k === medidaProductos())[1];
const unidadPrecio = (um) => um ? `/${esc(um)}` : '';
function cantidadProducto(a) {
  return a.mezcla ? '<span class="igual" title="Compras en distintas unidades">Unidades distintas</span>'
    : `${finito(a.cant) ? cantTxt(a.cant) : '—'}${a.um ? ` <small>${esc(a.um)}</small>` : ''}`;
}
function precioProducto(a) {
  return a.mezcla ? '<span class="igual" title="Compras en distintas unidades">—</span>' : `${precio(a.precio)}${finito(a.precio) ? `<small>${unidadPrecio(a.um)}</small>` : ''}`;
}
function celdaMedidas(a, medida) {
  if (!a.valor && !a.cant) return '<span class="pv-celda z">—</span>';
  return `<span class="pv-celda" data-cant="${a.cant ?? ''}" data-precio="${a.precio ?? ''}" data-valor="${a.valor}">`
    + `<span class="pv-cantidad">${cantidadProducto(a)}</span><span class="pv-precio">${precioProducto(a)}</span>`
    + (medida === 'tres' ? `<span class="pv-valor">${soles(a.valor)}</span>` : '') + '</span>';
}

// «Total del rango»: los productos comprados al proveedor en el rango. El
// producto en foco se despliega con sus proveedores de los últimos 90 días
// (precio promedio del período) y, abajo, los de todo el histórico.
function tablaProductos(F, R, X, colores) {
  const { p, ci, prod } = X;
  const medida = medidaProductos();
  const columnas = { valor: ['valor', 'pct', 'hab'], cant: ['cant'], precio: ['precio', 'hab'], ambos: ['cant', 'precio'], tres: ['cant', 'precio', 'valor'] }[medida];
  const titulos = { valor: 'Valor comprado (S/)', pct: '%', cant: 'Cantidad', precio: 'Precio unitario', hab: 'Vs. habitual' };
  const g = new Map();
  ci.ls.forEach((l) => {
    const a = g.get(l.prod) || { prod: l.prod, valor: 0, cant: 0, ls: [] };
    a.valor += l.valor; a.cant += l.cant; a.ls.push(l);
    g.set(l.prod, a);
  });
  const rows = [...g.values()].sort((a, b) => b.valor - a.valor);
  if (!rows.length) return { n: 0, html: '<div class="nota-v">Sin productos para este proveedor.</div>' };
  const tot = suma(rows, (a) => a.valor) || 1;
  const filas = rows.map((a) => {
    const nom = F.prods[a.prod], hab = ci.hab.get(a.prod), m = medidasDe(a.ls, F);
    let vh;
    if (!finito(hab)) vh = '<span class="var">—</span>';
    else if (Math.abs(hab) < 0.5) vh = '<span class="var igual" title="Igual al precio habitual (±0,5 %)">=</span>';
    else vh = `<span class="var ${hab > 0 ? 'sube' : 'baja'}">${fmtVar(hab)}</span>`;
    const foco = a.prod === prod, solo = G.pan && G.pan.pv90.get(a.prod) && G.pan.pv90.get(a.prod).size === 1;
    const valores = { valor: soles(a.valor), pct: `${Math.round(a.valor / tot * 100)} %`, cant: cantidadProducto(m), precio: precioProducto(m), hab: vh };
    return `<div class="ft-f${foco ? ' foco' : ''}" data-acc="prod" data-v="${a.prod}" title="${esc(nom)}${solo ? ' · en 90 días, sólo a este proveedor' : ''} · clic: sus proveedores y su curva">`
      + celda(esc(nom), 'nm') + columnas.map((k) => celda(valores[k], `r pv-${k}`)).join('') + '</div>'
      + (foco ? `<div class="lf-sub pl-provs">${provsDelProducto(F, R, a.prod, colores)}</div>` : '');
  });
  return { n: rows.length, html: tabla(`pl pl-${medida}`, [celda('Producto'), ...columnas.map((k) => celda(titulos[k], 'r', k === 'precio' ? 'Valor comprado dividido entre cantidad, en la unidad de compra del producto'
      : k === 'hab' ? 'Contra la mediana del precio de los 90 días anteriores a cada compra, sin las compras para revisar' : ''))], filas,
    [celda(`${rows.length} ${rows.length === 1 ? 'producto' : 'productos'}`, 'nm'), ...columnas.map((k) => celda(k === 'valor' ? soles(suma(rows, (a) => a.valor)) : k === 'pct' ? '100 %' : '', 'r'))]) };
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
    const marca = r9.length < 2 ? '' : Math.abs(dif) < 0.05 ? '<i class="chip barato">el más bajo</i>' : `<span class="igual">+${dif.toFixed(1)} %</span>`;
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
  const medidaTabla = medidaProductos();
  if (medidaTabla === 'ambos' || medidaTabla === 'tres') return tablaDesgloseCombinado(F, X, medidaTabla);
  const D = desglose(F, C, F.P[X.p], medidaTabla);
  if (!D.vis.length) return '<div class="nota-v">La curva no tiene períodos que desglosar.</div>';
  if (!D.filas.length) return '<div class="nota-v">Sin compras a este proveedor en los últimos períodos de la curva.</div>';
  if (medidaTabla !== 'valor') D.filas.forEach((a) => {
    const unidad = medidasDe(a.ls, F);
    if (unidad.mezcla) { a.m = a.m.map(() => null); a.um = 'Unidades distintas'; }
  });
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
      return `<span class="r">${filaVar(varPct(u, rv), medida === 'precio')}</span>`;
    }
    return `<span class="r">${filaVar(varPct(u, serie.length > 1 ? serie[serie.length - 2] : null), medida === 'precio')}</span>`;
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
    return `<div class="ft-f pm-f${a.prod === prod ? ' foco' : ''}" data-acc="prod-curva" data-v="${a.prod}" title="${esc(nom)} · clic: su curva">`
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
  const que = { valor: 'Valor comprado (S/)', cant: 'Cantidad', precio: 'Precio unitario promedio' }[medida];
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

function tablaDesgloseCombinado(F, X, medida) {
  const C = X.C, D = desglose(F, C, F.P[X.p], 'valor');
  if (!D.vis.length) return '<div class="nota-v">Sin períodos para desglosar.</div>';
  if (!D.filas.length) return '<div class="nota-v">Sin compras a este proveedor en los períodos visibles.</div>';
  const vis = new Set(D.vis), filas = D.filas.map((a) => {
    const nombre = F.prods[a.prod], visibles = a.ls.filter((l) => vis.has(l.k));
    return `<div class="ft-f pm-f${a.prod === X.prod ? ' foco' : ''}" data-acc="prod-curva" data-v="${a.prod}" title="${esc(nombre)} · clic: su curva">`
      + celda(esc(nombre), 'nm') + D.vis.map((k) => celdaMedidas(medidasDe(a.ls.filter((l) => l.k === k), F), medida)).join('')
      + celdaMedidas(medidasDe(visibles, F), medida) + '</div>';
  });
  const head = D.vis.map((k, i) => C.parc && i === D.vis.length - 1 ? C.parc.rot : etq(k, C.gran, false, F));
  const total = medida === 'tres' ? `<div class="ft-f ft-t">${celda('Valor comprado (S/)', 'nm')}${D.total.map((v) => celda(soles(v), 'r')).join('')}${celda(soles(suma(D.total, (v) => v)), 'r')}</div>` : '';
  return `<div class="nota pv-leyenda"><b>Cantidad</b> arriba · <b>Precio unitario promedio</b> debajo${medida === 'tres' ? ' · valor comprado al final' : ''} · ${D.vis.length} últimos períodos visibles</div>`
    + `<div class="ft pm pm-combinado" style="--n:${D.vis.length}"><div class="ft-f ft-h">${celda('Producto')}${head.map((h) => celda(esc(h), 'r')).join('')}${celda('Total visible', 'r', 'Cantidad y precio ponderado de los períodos visibles')}</div>`
    + `<div class="ft-l">${filas.join('')}</div>${total}</div>`;
}

function controlesTiempo(C, fijo = false) {
  const st = G.st, option = (k, texto, on) => `<option value="${k}"${on ? ' selected' : ''}>${texto}</option>`;
  const disabled = fijo ? ' disabled' : '';
  return `<label class="pv-control"><span>Agrupar por</span><select class="lf-men" data-sel="gran" aria-label="Agrupar"${disabled}>${GRANOS.map(([k, t]) => option(k, t, k === st.gran)).join('')}</select></label>`
    + `<label class="pv-control"><span>Período</span><select class="lf-men" data-sel="op" aria-label="Período de la vista"${disabled}>${OPS.map(([k, t]) => option(k, k === 'Rango' ? 'Rango del reporte' : k === 'Todo' ? 'Todo el historial' : `Últimos ${t}`, k === (fijo ? 'Rango' : st.op))).join('')}</select></label>`;
}
function controlesPuntos(C) {
  if (!C.win) return '';
  const w = C.win, fmtW = (o) => o == null ? `Automático (${Math.min(VENTANA_AUTO, w.nPer)})` : o === w.nPer ? `Todos (${w.nPer})` : String(o);
  return `<div class="lf-ev pv-puntos"><label class="pv-control"><span>Puntos de la curva</span><select class="lf-men" data-sel="win" aria-label="Períodos visibles">${w.ops.map((o) => `<option value="${o ?? ''}"${o === w.tam ? ' selected' : ''}>${fmtW(o)}</option>`).join('')}</select></label>`
    + `<button class="lf-pil lf-fl1" data-acc="mover" data-v="-1" title="Períodos anteriores"${w.ini <= 0 ? ' disabled' : ''}>‹</button>`
    + `<button class="lf-pil lf-fl1" data-acc="mover" data-v="1" title="Períodos siguientes"${w.ini >= w.iniMax ? ' disabled' : ''}>›</button></div>`;
}
function contextoTiempo(F, R, C, fijo = false) {
  if (fijo || !C.hist) return `Rango del reporte · ${tramo(R.R0, R.R1)}`;
  const [ini, fin] = ventana(C.op, F.ULT, F.MIN);
  return `Histórico · ${fDMA(inicioDe(ini, C.gran))}–${fDMA(fin)}`;
}

function tablaDocumentos(F, X, per) {
  const { ci, p, C } = X;
  const ls = (per ? C.deP.filter((l) => l.k === per) : ci.ls).filter((l) => !l.sinDoc);
  if (!ls.length) return { n: 0, html: `<div class="nota-v">Sin números de documento para este proveedor en ${per ? 'ese período' : 'el rango'}.</div>` };
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
      subio = `<span class="var sube">+${s.dp.toFixed(1)} %</span> ${esc(F.prods[s.prod])}${n > 1 ? ` <small>y ${n - 1} más</small>` : ''}`;
    }
    const lin = [...a.prods.values()].sort((x, y) => y.valor - x.valor).map((b) => {
      const um = F.umsRaw[b.um] ? F.ums[b.um] : '';
      return `<div class="dl-l">${celda(esc(F.prods[b.prod]), 'nm', F.prods[b.prod])}${celda(cantTxt(b.cant) + (um ? ` ${esc(um)}` : ''), 'r')}`
        + `${celda(b.cant ? precio(b.valor / b.cant) : '—', 'r')}${celda(soles(b.valor), 'r')}</div>`;
    }).join('');
    return `<details class="dl" data-k="${k}"${G.st.abiertos.has(k) ? ' open' : ''}><summary class="ft-f">`
      + `${celda(fCorta(a.fecha))}${celda(esc(F.docs[a.doc]), 'nm')}${celda(String(a.prods.size), 'r')}${celda(soles(a.valor), 'r')}`
      + `${celda(dias == null ? '—' : String(dias), 'r')}<span class="nm" title="${s ? esc(F.prods[s.prod]) : ''}">${subio}</span>`
      + '<span class="ch">▾</span></summary><div class="lf-sub dl-d"><div class="dl-l enc"><span>Producto</span><span class="r">Cant.</span>'
      + `<span class="r">P. unit.</span><span class="r">Valor</span></div>${lin}</div></details>`;
  });
  const tot = suma(docs, (a) => a.valor);
  return { n: docs.length, html: tabla('dd', [celda('Fecha'), celda('Documento'), celda('Prods', 'r', 'Productos distintos en el documento'), celda('Valor', 'r'),
      celda('Días', 'r', 'Desde la compra anterior'), celda('Subió de precio', '', 'Contra la compra anterior del mismo producto a este proveedor'), celda('')], filas,
    [celda(`Total · ${num(docs.length, 0)} · ticket ${soles(tot / docs.length)}`, 'nm tot3'),
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
      + `<span class="r">${filaVar(v)}</span><span class="ch">▾</span></summary><div class="lf-sub dl-d">`
      + (ds.length ? '<div class="dl-l per enc"><span>Fecha</span><span>Documento</span><span class="r">Filas</span><span class="r">Total</span></div>'
        + ds.map((a) => `<div class="dl-l per">${celda(fDMA(a.fecha))}${celda(esc(F.docs[a.doc]), 'nm')}${celda(String(a.filas), 'r')}${celda(soles(a.valor), 'r')}</div>`).join('')
        : '<div class="nota-v">Sin documentos en el período.</div>') + '</div></details>');
  }
  const nd = suma(nDocs, (s) => s.size), tv = suma(vals, (x) => x);
  return tabla('dp', [celda('Período'), celda('Docs', 'r'), celda('Valor', 'r'), celda('Var. %', 'r'), celda('')],
    filas, [celda(`Total · ${num(nd, 0)} ${nd === 1 ? 'documento' : 'documentos'}`, 'nm'), celda(''), celda(soles(tv), 'r'), celda(''), celda('')]);
}

function fichaHtml() {
  const { F, R, st } = G, X = G.X, { p, prod, ci, C, rk } = X, D = G.pan.det.get(p);
  const nom = F.noms[p], H = F.P[p], desde = H.length ? H[0].d : null;
  const colores = new Map(rk.top.map((q, i) => [q, i]));
  const f = rk.filas.find((x) => x.p === p) || rk.yaNo.find((x) => x.p === p) || { prev: 0, valor: 0, est: '' };
  const ant = tramo(R.R0 - rk.dias, R.R0 - 1);
  const cf = (rot, val, cls, sub, ayuda) => `<div class="lf-cf"${ayuda ? ` title="${esc(ayuda)}"` : ''}><span>${esc(rot)}</span><b class="${cls || ''}">${esc(val)}</b><small>${esc(sub)}</small></div>`;
  const ppv = ci.ppv;
  const cifrasH = cf('Compra', soles(ci.compra), '', `${(ci.compra / rk.totAll * 100).toFixed(1)} % de lo comprado`)
    + cf(`Vs. ${rk.dias} días antes`, f.est ? f.est : (f.prev > 0 ? fmtVar(varPct(ci.compra, f.prev)) : '—'), '', `${soles(f.prev)} · ${ant}`, 'Comprar más o menos no es bueno ni malo: por eso va en gris.')
    + cf('Precio', ppv == null ? '—' : solesG(ppv), colorPpv(ppv), 'contra lo habitual', 'Lo pagado de más o de menos contra el precio habitual de cada compra (la mediana de los 90 días anteriores), sin las compras para revisar: la misma cuenta de Precios.')
    + cf('Documentos', num(ci.docs, 0), '', ci.docs ? `ticket ${soles(ci.compra / ci.docs)}` : 'sin número');
  const frase = [];
  if (D && D.solos.size) frase.push(`${D.solos.size} de sus ${new Set(ci.ls.map((l) => l.prod)).size} productos sólo se los compraste a este proveedor en 90 días (${soles(D.vSolo)}).`);
  const porPd = new Map();
  ci.ls.forEach((l) => { if (vale(l)) porPd.set(l.prod, (porPd.get(l.prod) || 0) + l.valor - l.ref * l.cant); });
  const ord = [...porPd].filter((a) => Math.abs(a[1]) >= 1).sort((a, b) => b[1] - a[1]);
  if (ord.length && ord[0][1] > 0) frase.push(`Lo que más subió: ${F.prods[ord[0][0]]}, ${solesG(ord[0][1])}.`);
  if (ord.length && ord[ord.length - 1][1] < 0) frase.push(`Lo que más bajó: ${F.prods[ord[ord.length - 1][0]]}, ${solesG(ord[ord.length - 1][1])}.`);
  if (D && D.nfl) frase.push(`${D.nfl} ${D.nfl === 1 ? 'línea para revisar no entra' : 'líneas para revisar no entran'} en el precio.`);
  if (!ci.ls.length) frase.push(`No se le compró en este rango. Antes: ${soles(f.prev)}.`);
  const nProd = new Set(ci.ls.map((l) => l.prod)).size;
  const per = st.per && C.keys.includes(st.per) ? st.per : null;
  const tabs = [['curva', 'Curva'], ['prod', `Productos · ${nProd}`], ['doc', `Documentos · ${ci.docs}`]]
    .map(([k, t]) => `<button class="${k === st.tab ? 'on' : ''}" data-acc="tab" data-v="${k}" aria-pressed="${k === st.tab}">${esc(t)}</button>`).join('');
  const chips = (prod != null ? `<button class="lf-quita" data-acc="soltar-prod" title="${esc(F.prods[prod])}">${esc(F.prods[prod])} ✕</button>` : '')
    + (per && st.tab === 'doc' ? `<button class="lf-quita" data-acc="soltar-per">${esc(etqLarga(per, C, F))} ✕</button>` : '');
  let zona = '';
  if (st.tab === 'curva') zona = zonaCurva(F, C, prod, per);
  else if (st.tab === 'prod') {
    const fijo = st.pmodo === 'tot';
    const sel = `<label class="pv-control"><span>Ver</span><select class="lf-men" data-sel="pmodo" aria-label="Cómo ver los productos">${[['per', 'Desglose por período'], ['tot', 'Total del rango']].map(([k, t]) => `<option value="${k}"${k === st.pmodo ? ' selected' : ''}>${t}</option>`).join('')}</select></label>`;
    const medir = `<label class="pv-control"><span>Mostrar</span><select class="lf-men" data-sel="pmedida" aria-label="Medida de los productos">${MEDIDAS_PRODUCTOS.map(([k, t]) => `<option value="${k}"${k === medidaProductos() ? ' selected' : ''}>${t}</option>`).join('')}</select></label>`;
    zona = `<div class="pv-controles">${sel}${controlesTiempo(C, fijo)}${medir}${fijo ? '' : controlesPuntos(C)}</div>`
      + `<div class="pv-contexto"><b>${esc(tituloMedidaProductos())}</b><span>${esc(contextoTiempo(F, R, C, fijo))}</span></div>`
      + `<div class="cuerpo">${fijo ? tablaProductos(F, R, X, colores).html : tablaDesglose(F, X)}</div>`;
  } else {
    const sel = `<select class="lf-men" data-sel="dmodo" aria-label="Cómo ver los documentos">${[['doc', 'Ver: Por documento'], ['per', 'Ver: Por período']].map(([k, t]) => `<option value="${k}"${k === st.dmodo ? ' selected' : ''}>${t}</option>`).join('')}</select>`;
    const porPer = st.dmodo === 'per';
    zona = `<div class="lf-ev">${sel}<span class="sub">${porPer ? contextoTiempo(F, R, C) : per ? 'De ese período. Clic: sus líneas' : 'Del rango. Clic: sus líneas'}</span></div>`
      + (porPer ? `<div class="pv-controles">${controlesTiempo(C)}${controlesPuntos(C)}</div>` : '')
      + `<div class="cuerpo">${porPer ? tablaDocsPeriodo(F, X) : tablaDocumentos(F, X, per).html}</div>`;
  }
  return `<div class="lf-fcab"><div class="lf-ftit"><span class="lf-miga">Proveedor${desde != null ? ` · desde ${mesAnio(desde)}` : ''}</span><h3 title="${esc(nom)}">${esc(nom)}</h3></div>`
    + `${lfAmp('panel', st.amp === 'panel', 'la ficha')}<button class="lf-quita" data-acc="soltar">Soltar</button></div>`
    + `<div class="lf-cifras">${cifrasH}</div>${frase.length ? `<p class="lf-frase">${esc(frase.join(' '))}</p>` : ''}`
    + `<div class="lf-fl"><span class="lf-seg" role="group" aria-label="Qué mirar">${tabs}</span>${chips}</div><div class="lf-zona">${zona}</div>`;
}

function zonaCurva(F, C, prod, per) {
  const st = G.st;
  const op = (v, t, on) => `<option value="${v}"${on ? ' selected' : ''}>${t}</option>`;
  let ctl = controlesTiempo(C);
  if (prod != null) ctl += `<label class="pv-control"><span>Medir</span><select class="lf-men" data-sel="medida" aria-label="Qué medir">${MEDIDAS.map(([k, t]) => op(k, t, k === st.medida)).join('')}</select></label>`;
  let graf;
  if (!C.keys.length) graf = '<div class="lf-sinc">Sin compras de este proveedor en la ventana.</div>';
  else {
    const fmt = (y) => esc(fmtMedida(y, C.medida, C.um)), precioMed = C.medida === 'precio';
    graf = lfCurva({ etqs: C.keys.map((k) => esc(etq(k, C.gran, true, F))), ys: precioMed ? C.ys.map(() => null) : C.ys, claves: C.keys, acc: 'per-curva',
      parcial: !!C.parc, refY: precioMed ? null : C.ref, foco: per, rotY: fmt, linea: precioMed ? C.ys : null });
  }
  const n = C.keys.length, ley = [];
  if (C.parc && n) {
    ley.push(`${C.parc.rot} en curso: ${fmtMedida(C.ys[n - 1], C.medida, C.um)}`);
    if (C.medida === 'precio') ley.push(`contra el período anterior entero: ${fmtVar(varPct(C.ys[n - 1], n > 1 ? C.ys[n - 2] : null))}`);
    else ley.push(`${C.parc.rotRef}: ${fmtMedida(C.ref, C.medida, C.um)} ${fmtVar(varPct(C.ys[n - 1], C.ref))}`);
  }
  if (prod == null) ley.push('Para cantidad y precio, elige un producto en «Productos».');
  return `<div class="pv-controles">${ctl}${controlesPuntos(C)}</div><p class="lf-nota">${esc(contextoTiempo(F, G.R, C))}</p>${graf}<p class="lf-nota">${esc(ley.join(' · '))}</p>`;
}

// El globo de un período: su cifra, contra qué, y lo que hace el clic.
function pintarTip(k) {
  const raiz = G.raiz, C = G.X && G.X.C;
  if (!raiz || !C) return;
  const i = k == null ? -1 : C.keys.indexOf(k), n = C.keys.length;
  if (i < 0) { lfTip(raiz, null); return; }
  const esParc = C.parc && i === n - 1;
  const rot = esParc ? `${C.parc.rot} (en curso)` : (C.gran === 'Mes' ? mesAnio(dn(`${k}-01`)) : etq(k, C.gran, false, G.F));
  const cmp = esParc && C.medida !== 'precio' ? varPct(C.ys[i], C.ref) : varPct(C.ys[i], i ? C.ys[i - 1] : null);
  const fila = (a, b) => `<span><i>${esc(a)}</i>${esc(b)}</span>`;
  let html = `<b>${esc(rot)}</b>` + fila(C.medida === 'cant' ? 'Cantidad' : C.medida === 'precio' ? 'Precio' : 'Compra', fmtMedida(C.ys[i], C.medida, C.um))
    + fila(esParc && C.medida !== 'precio' ? `Contra ${C.parc.rotRef}` : 'Contra el anterior', fmtVar(cmp));
  if (C.medida === 'valor' && C.gran !== 'Documento') html += fila('Del total comprado', `${(C.v[i] / (C.tot[i] || 1) * 100).toFixed(1)} %`);
  html += `${fila('Documentos', String(C.docs[i]))}<em>clic: sus documentos</em>`;
  lfTip(raiz, i, n, html);
}

function listaVisible() {
  const { F, R, st } = G, rk = G.X.rk, pan = G.pan, q = st.q || '';
  const ok = (f) => !q || coincide(f.p < 0 ? `Otros ${f.otros}` : F.noms[f.p], q);
  const base = rk.filas.filter(ok), reales = base.filter((f) => f.p >= 0);
  const vT = suma(reales, (f) => f.valor) || 1;
  const en80 = new Set(); let ac = 0;
  [...reales].sort((a, b) => b.valor - a.valor).forEach((f) => { if (ac / vT < 0.8) en80.add(f.p); ac += f.valor; });
  const det = (f) => pan.det.get(f.p) || { ppv: 0, hay: false, solos: new Set(), vSolo: 0 };
  const nv = reales.filter((f) => f.est), sub = reales.filter((f) => det(f).ppv > 1), baj = reales.filter((f) => det(f).ppv < -1), sol = reales.filter((f) => det(f).solos.size);
  const yaNo = rk.yaNo.filter(ok);
  let vis = st.kpi === 'sube' ? sub : st.kpi === 'baja' ? baj : st.kpi === 'solo' ? sol : base;
  if (st.ver === 'n80') vis = vis.filter((f) => en80.has(f.p));
  else if (st.ver === 'nv') vis = vis.filter((f) => f.est);
  else if (st.ver === 'ya') vis = [...yaNo].sort((a, b) => b.prev - a.prev);
  const s = st.sort;
  const clave2 = s ? { nom: (f) => (f.p < 0 ? '~' : sinTildes(F.noms[f.p])), val: (f) => f.valor, ant: (f) => f.valor - f.prev, ppv: (f) => det(f).ppv, pro: (f) => (det(f).prods ? det(f).prods.size : 0) }[s.col] : null;
  vis = [...vis].sort(clave2 ? (a, b) => { const x = clave2(a), y = clave2(b); return (x < y ? -1 : x > y ? 1 : 0) * s.dir; }
    : st.kpi === 'sube' ? (a, b) => det(b).ppv - det(a).ppv : st.kpi === 'baja' ? (a, b) => det(a).ppv - det(b).ppv
      : st.kpi === 'solo' ? (a, b) => det(b).vSolo - det(a).vSolo : (a, b) => b.valor - a.valor);
  const solos = new Set(); sol.forEach((f) => det(f).solos.forEach((x) => solos.add(x)));
  return { base, reales, vT, en80, nv, sub, baj, sol, yaNo, vis, det, solos, sumaPpv: (xs) => suma(xs, (f) => det(f).ppv), vSolo: suma(sol, (f) => det(f).vSolo) };
}

function kpisHtml(V) {
  const { st } = G, kp = (id, rot, val, d, tip, vc) => `<button class="lf-kpi${st.kpi === id ? ' on' : ''}" data-acc="kpi" data-v="${id}" aria-pressed="${st.kpi === id}" title="${esc(tip)}"><span class="r">${esc(rot)}</span><span class="v ${vc}">${esc(val)}</span><span class="d">${esc(d)}</span></button>`;
  const nP = (n) => `${num(n, 0)} ${n === 1 ? 'proveedor' : 'proveedores'}`;
  return kp('todos', 'Proveedores', num(V.reales.length, 0), `${soles(V.vT)} · ${V.en80.size} hacen el 80 %`, 'Lo comprado en el rango, sin IGV.', '')
    + kp('sube', 'Subieron el precio', solesG(V.sumaPpv(V.sub)), `${nP(V.sub.length)} · contra lo habitual`, 'Lo pagado de más contra el precio habitual de cada compra. Sin las compras para revisar: es la misma cuenta de Precios.', 'rojo')
    + kp('baja', 'Bajaron el precio', solesG(V.sumaPpv(V.baj)), `${nP(V.baj.length)} · contra lo habitual`, 'Lo pagado de menos contra el precio habitual de cada compra.', 'verde')
    + kp('solo', 'Sólo se compran a uno', soles(V.vSolo), `${V.solos.size} productos · en 90 días nadie más los vendió`, 'Productos que en los últimos 90 días tuvieron un solo proveedor: si falla, no hay otro a la mano.', '');
}

function listaHtml(V) {
  const { F, R, st } = G, s = st.sort, amp = !!st.det, rk = G.X.rk;
  const th = (k, t, ayuda, cls) => `<th class="${cls}"${ayuda ? ` title="${esc(ayuda)}"` : ''}><button data-acc="orden" data-v="${k}">${esc(t)}${s && s.col === k ? (s.dir > 0 ? ' ↑' : ' ↓') : ''}</button></th>`;
  const tods = st.kpi === 'todos' && st.ver === 'todos';
  const vMax = Math.max(1, ...V.vis.map((f) => f.valor)), meses = mesesSpark(F);
  const tv = suma(V.vis, (f) => f.valor), tprev = tods ? suma(V.base, (f) => f.prev) + suma(V.yaNo, (f) => f.prev) : suma(V.vis, (f) => f.prev), tppv = V.sumaPpv(V.vis.filter((f) => f.p >= 0));
  let h = `<div class="lf-scroll" data-tabla="lista"><table class="lf-t"><thead><tr>${th('nom', 'Proveedor', '', 'l')}${th('val', 'Compra', '', 'w-im')}${amp ? th('val', '%', 'Del total comprado', 'w-pc') : ''}`
    + `${th('ant', 'Vs. antes', 'Contra el período anterior de igual largo. En soles: un % sobre casi nada no dice mucho.', 'w-im')}${th('ppv', 'Precio', 'Contra su precio habitual, la mediana de los 90 días anteriores: lo mismo que en Precios.', 'w-pr')}`
    + (amp ? `${th('pro', 'Prods', 'Productos comprados en el rango', 'w-n')}<th class="w-n">Docs</th><th class="w-pr">Ticket</th><th class="w-n">Cada</th><th class="w-n" title="Productos que en 90 días sólo se le compraron a él">Sólo él</th><th class="w-pr">Última</th><th class="w-t" title="Lo comprado en cada mes">13 meses</th>` : '')
    + '</tr></thead><tbody>';
  h += `<tr class="tot"><td class="l">Total · ${num(V.vis.length, 0)}</td><td>${soles(tv)}</td>${amp ? `<td>${Math.round(tv / V.vT * 100)} %</td>` : ''}`
    + `<td title="${tods && V.yaNo.length ? esc(`Con los ${V.yaNo.length} proveedores a los que ya no se les compró: ${soles(suma(V.yaNo, (f) => f.prev))}`) : ''}">${solesG(tv - tprev)}</td><td class="${colorPpv(tppv)}">${solesG(tppv)}</td>${amp ? '<td></td><td></td><td></td><td></td><td></td><td></td><td></td>' : ''}</tr>`;
  h += V.vis.map((f) => {
    if (f.p < 0) return `<tr class="apag"><td class="l">Otros · ${f.otros}</td><td>${soles(f.valor)}</td>${amp ? `<td>${Math.round(f.valor / V.vT * 100)} %</td>` : ''}<td></td><td></td>${amp ? '<td></td><td></td><td></td><td></td><td></td><td></td><td></td>' : ''}</tr>`;
    const d = V.det(f), nom = F.noms[f.p], nd = d.docs ? d.docs.size : 0, np = d.prods ? d.prods.size : 0;
    const ayudaAnt = f.ya ? `Sin compras en este rango. Antes: ${soles(f.prev)}` : f.est ? f.ayuda : `${soles(f.prev)} → ${soles(f.valor)} · ${fmtVar(varPct(f.valor, f.prev))}`;
    return `<tr class="${f.p === st.foco ? 'on' : ''}" data-acc="fila" data-v="${f.p}"><td class="l nm" title="${esc(nom)}">${esc(nom)}</td><td class="bv" style="--b:${(f.valor / vMax * 100).toFixed(1)}%">${soles(f.valor)}</td>${amp ? `<td class="gris">${f.valor ? `${Math.round(f.valor / V.vT * 100)} %` : '—'}</td>` : ''}`
      + `<td class="${f.est ? 'mar' : 'gris'}" title="${esc(ayudaAnt)}">${esc(f.est || solesG(f.valor - f.prev))}</td><td class="${colorPpv(d.ppv)} fuerte">${d.hay ? solesG(d.ppv) : '—'}</td>`
      + (amp ? `<td class="gris">${st.kpi === 'solo' ? `${d.solos.size} de ${np}` : np || '—'}</td><td class="gris">${nd || '—'}</td><td class="gris">${nd ? soles(f.valor / nd) : '—'}</td><td class="gris">${nd > 1 ? `${Math.round(rk.dias / nd)} d` : '—'}</td><td class="gris">${d.solos.size || '—'}</td><td class="gris">${d.ult != null ? fCorta(d.ult) : '—'}</td>`
        + `<td class="t"><svg viewBox="0 0 68 20" aria-hidden="true"><polyline points="${sparkDe(F, f.p, meses)}"></polyline></svg></td>` : '') + '</tr>';
  }).join('');
  if (!V.vis.length) h += `<tr><td colspan="${amp ? 12 : 4}" class="lf-vacio">Sin proveedores con ese filtro.</td></tr>`;
  return `${h}</tbody></table></div><div class="lf-pie"><p class="lf-nota">${num(V.vis.length, 0)} proveedores · sin IGV · contra ${esc(tramo(R.R0 - rk.dias, R.R0 - 1))}</p>${lfAmp('izq', st.amp === 'izq', 'la lista')}</div>`;
}

function mesesSpark(F) {
  if (F.mesesSp) return F.mesesSp;
  const fin = F.ULT, k = [], [y, m] = ymd(fin);
  for (let i = 12; i >= 0; i -= 1) { const t = new Date(Date.UTC(y, m - 1 - i, 1)); k.push(`${t.getUTCFullYear()}-${String(t.getUTCMonth() + 1).padStart(2, '0')}`); }
  F.mesesSp = k; F.sparks = new Map();
  return k;
}
function sparkDe(F, p, meses) {
  if (F.sparks.has(p)) return F.sparks.get(p);
  const por = new Map();
  F.P[p].forEach((l) => { const k = clave(l, 'Mes'); por.set(k, (por.get(k) || 0) + l.valor); });
  const v = lfSpark(meses.map((k) => por.get(k) || 0));
  F.sparks.set(p, v);
  return v;
}

// Sin nadie elegido, el panel responde la pregunta de la vista.
function resumenHtml(V) {
  const { F, R, st } = G, rk = G.X.rk, pan = G.pan;
  const item = (n, s, v, c, acc, val) => `<button class="lf-fi" data-acc="${acc}" data-v="${val}"><span class="n" title="${esc(n)}">${esc(n)}</span><small title="${esc(s)}">${esc(s)}</small><b class="${c}">${esc(v)}</b></button>`;
  const rango = `${fCorta(R.R0)} – ${fCorta(R.R1)}`;
  const cab = (t) => `<div class="lf-fcab"><div class="lf-ftit"><span class="lf-miga">Todos los proveedores · ${esc(rango)}</span><h3>${esc(t)}</h3></div>${lfAmp('panel', st.amp === 'panel', 'el resumen')}</div>`;
  const nP = (n) => `${num(n, 0)} ${n === 1 ? 'proveedor' : 'proveedores'}`;
  const pleg = (t, l) => { const ab = st.pleg[t] !== false; return lfPleg(t, esc(t), `<div class="lf-lista">${l}</div>`, ab).replace('lf-pleg', `lf-pleg${ab ? ' crece' : ''}`); };
  const dosListas = (t1, l1, t2, l2) => pleg(t1, l1) + (t2 ? pleg(t2, l2) : '');
  let h;
  if (st.kpi === 'solo') {
    const porPd = new Map();
    F.todas.forEach((l) => { if (l.d >= R.R0 && l.d <= R.R1 && pan.pv90.get(l.prod) && pan.pv90.get(l.prod).size === 1) {
      const a = porPd.get(l.prod) || { prod: l.prod, p: l.p, v: 0, docs: new Set() }; a.v += l.valor; a.docs.add(l.doc); porPd.set(l.prod, a); } });
    const visibles = new Set(V.reales.map((f) => f.p)), xs = [...porPd.values()].filter((a) => visibles.has(a.p)).sort((a, b) => b.v - a.v), una = xs.filter((a) => a.docs.size === 1);
    h = cab('De quién dependes') + `<p class="lf-frase">${esc(`${xs.length} productos tuvieron un solo proveedor en 90 días: ${soles(suma(xs, (a) => a.v))}. Ojo: ${una.length} de ellos se compraron una sola vez, así que no todos son una dependencia de verdad.`)}</p>`
      + dosListas('Los que más pesan', xs.slice(0, 40).map((a) => item(F.prods[a.prod], F.noms[a.p], soles(a.v), '', 'fila', a.p)).join(''));
  } else if (st.kpi === 'sube' || st.kpi === 'baja') {
    const signo = st.kpi === 'sube' ? 1 : -1, lst = st.kpi === 'sube' ? V.sub : V.baj, porPd = new Map(), visibles = new Set(V.reales.map((f) => f.p));
    F.todas.forEach((l) => { if (l.d >= R.R0 && l.d <= R.R1 && vale(l) && visibles.has(l.p)) { const k = `${l.prod}|${l.p}`, a = porPd.get(k) || { prod: l.prod, p: l.p, x: 0 }; a.x += l.valor - l.ref * l.cant; porPd.set(k, a); } });
    const xs = [...porPd.values()].filter((a) => a.x * signo > 0).sort((a, b) => (b.x - a.x) * signo);
    h = cab(st.kpi === 'sube' ? 'Quién subió el precio' : 'Quién bajó el precio') + `<p class="lf-frase">${esc(`${nP(lst.length)} sumaron ${solesG(V.sumaPpv(lst))} contra lo habitual. Se mide compra por compra, contra la mediana de los 90 días anteriores de ese producto; sin las compras para revisar.`)}</p>`
      + dosListas('Producto por producto', xs.slice(0, 40).map((a) => item(F.prods[a.prod], F.noms[a.p], solesG(a.x), colorPpv(a.x), 'fila', a.p)).join(''));
  } else {
    const neto = V.sumaPpv(V.reales), ordS = [...V.sub].sort((a, b) => V.det(b).ppv - V.det(a).ppv).slice(0, 6), ordB = [...V.baj].sort((a, b) => V.det(a).ppv - V.det(b).ppv).slice(0, 6);
    const pr = (f) => { const n = V.det(f).prods.size; return `${n} ${n === 1 ? 'prod' : 'prods'}`; };
    h = cab('A quién le compras') + `<p class="lf-frase">${esc(`${V.en80.size} de ${nP(V.reales.length)} hacen el 80 % de lo comprado. Contra tu precio habitual, ${V.sub.length} subieron ${solesG(V.sumaPpv(V.sub))} y ${V.baj.length} bajaron ${solesG(V.sumaPpv(V.baj))}: en total pagaste ${soles(Math.abs(neto))} ${neto < 0 ? 'menos' : 'más'} de lo habitual.${V.yaNo.length ? ` A ${V.yaNo.length} proveedores del período anterior ya no se les compró (${soles(suma(V.yaNo, (f) => f.prev))}).` : ''}`)}</p>`
      + dosListas('Los que más subieron', ordS.map((f) => item(F.noms[f.p], pr(f), solesG(V.det(f).ppv), 'rojo', 'fila', f.p)).join(''), 'Los que más bajaron', ordB.map((f) => item(F.noms[f.p], pr(f), solesG(V.det(f).ppv), 'verde', 'fila', f.p)).join(''));
  }
  return h + lfFuera(G.R.pagina, soles, esc);
}

function pintar() {
  const { R, F, st } = G, raiz = G.raiz;
  if (!raiz) return;
  if (!st.pleg) st.pleg = {};
  if (!R || !F || R.sello !== F.sello) { if (!raiz.innerHTML) raiz.innerHTML = '<div class="lf-vacio">Cargando…</div>'; return; }
  G.X = st.foco != null ? calcular(F, R, st) : { rk: ranking(F, R) };
  G.panK = `${F.sello}|${R.R0}|${R.R1}`;
  if (!G.pan || G.pan.k !== G.panK) { G.pan = panorama(F, R); G.pan.k = G.panK; }
  const V = listaVisible();
  G.V = V;
  const yL = raiz.querySelector('[data-tabla="lista"]')?.scrollTop || 0, yF = raiz.querySelector('.ft-l')?.scrollTop || 0, yR = raiz.querySelector('.lf-lista')?.scrollTop || 0;
  const foco = raiz.querySelector('.lf-busca:focus'), sel = foco ? [foco.selectionStart, foco.selectionEnd] : null;
  const verIzq = st.amp !== 'panel', verPanel = st.amp !== 'izq';
  const tods = [['todos', `Todos · ${V.reales.length}`, ''], ['n80', `Hacen el 80 % · ${V.en80.size}`, 'Los que suman el 80 % de lo comprado'], ['nv', `Nuevos o vuelven · ${V.nv.length}`, 'Sin compras en el período anterior'], ['ya', `Ya no · ${V.yaNo.length}`, 'Se les compró en el período anterior y en este no']];
  const chip = st.kpi !== 'todos' ? `<button class="lf-quita" data-acc="kpi" data-v="${st.kpi}">${{ sube: 'Subieron', baja: 'Bajaron', solo: 'Sólo a uno' }[st.kpi]} ✕</button>` : '';
  let h = `<div class="lf-main${st.det ? ' det' : ''}${st.amp ? ' amp' : ''}">${lfNivel2(tods, st.ver, st.det, st.como, comoHtml(R))}`
    + `<div class="lf-cab"><span class="lf-lugar" aria-hidden="true"></span>${lfMenuFamilias(R.pagina, st.menu === 'fam', soles, esc)}${chip}<span class="lf-esp"></span>`
    + `<input class="lf-busca" type="search" value="${esc(st.q || '')}" placeholder="Buscar proveedor…" aria-label="Buscar proveedor"><button class="lf-pil" data-acc="excel" title="Baja lo que se ve">Excel ↓</button></div>`
    + `<div class="lf-kpis">${kpisHtml(V)}</div><div class="lf-cuerpo" data-amp="${st.amp || ''}">`;
  if (verIzq) h += `<div class="lf-izq">${listaHtml(V)}</div>`;
  if (verPanel) h += `<aside class="lf-panel" aria-label="Ficha">${st.foco != null && G.X.p != null ? fichaHtml() : resumenHtml(V)}</aside>`;
  raiz.innerHTML = `${h}</div></div>`;
  const pon = (q, y) => { const e = raiz.querySelector(q); if (e) e.scrollTop = y; };
  pon('[data-tabla="lista"]', yL);
  if (G.reseteaF) G.reseteaF = false; else pon('.ft-l', yF);
  pon('.lf-lista', yR);
  if (sel) { const e = raiz.querySelector('.lf-busca'); e.focus({ preventScroll: true }); e.setSelectionRange(...sel); }
  lfPasarFecha(raiz, '.st-key-cp_prov_nativa_fecha');
}

// ── Los clics ────────────────────────────────────────────────────────────
function accion(acc, val, b) {
  const st = G.st;
  if (acc === 'menu') { st.menu = st.menu === val ? null : val; if (!st.menu) avisarFamilias(); pintar(); return; }
  if (st.menu) { st.menu = null; avisarFamilias(); }
  if (acc !== 'como') st.como = false;
  if (acc === 'detalle') { st.det = !!(b && b.checked); lfGuardar('cp_prov_det', st.det); }
  else if (acc === 'como') st.como = !st.como;
  else if (acc === 'pleg') { st.pleg = { ...st.pleg, [val]: st.pleg[val] === false }; lfGuardar('cp_prov_pleg', st.pleg); }
  else if (acc === 'orden') {
    const s = st.sort, d0 = val === 'nom' ? 1 : -1;
    st.sort = !s || s.col !== val ? { col: val, dir: d0 } : s.dir === d0 ? { col: val, dir: -s.dir } : null;
  } else if (acc === 'fila') {
    const p = +val;
    st.foco = st.foco === p ? null : p; st.prod = null; st.per = null; G.reseteaF = true;
    if (st.amp === 'izq') st.amp = null;
    if (st.foco == null && st.amp === 'panel') st.amp = null;
  } else if (acc === 'excel') { excelRank(); return; }
  else if (acc === 'kpi') { st.kpi = st.kpi === val ? 'todos' : val; st.foco = null; st.sort = null; }
  else if (acc === 'ver') { st.ver = val; }
  else if (acc === 'amp') { st.amp = st.amp === val ? null : val; }
  else if (acc === 'soltar') { st.foco = null; st.prod = null; st.per = null; if (st.amp === 'panel') st.amp = null; }
  else if (acc === 'soltar-prod') { st.prod = null; st.medida = 'valor'; }
  else if (acc === 'soltar-per') { st.per = null; }
  else if (acc === 'sumar') { const pa = G.R.pagina; pa.elegidas = pa.todas.map((x) => x[0]); G.pendFam = pa.elegidas.slice(); avisarFamilias(); return; }
  else if (acc === 'mover') { const w = G.X.C && G.X.C.win; if (w) st.winIni = Math.min(Math.max(0, w.ini + (+val) * w.ven), w.iniMax); }
  else if (acc === 'tab') { st.tab = val; G.reseteaF = true; }
  else if (acc === 'prod' || acc === 'prod-curva') { const i = +val; st.prod = st.prod === i ? null : i; if (st.prod == null) st.medida = 'valor'; }
  else if (acc === 'per-curva') {
    const C = G.X.C;
    st.tab = 'doc'; st.dmodo = 'doc'; st.per = val; G.reseteaF = true;
    if (C.gran === 'Documento') st.abiertos.add(`doc|${+val.split('|')[1]}`);
  } else return;
  pintar();
}
function avisarFamilias() {
  if (G.pendFam && G.enviar) { const x = G.pendFam; G.pendFam = null; G.enviar('familias', x); }
}
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.disabled) {
      if (G.st.menu && !(ev.target.closest && ev.target.closest('.lf-ms'))) { G.st.menu = null; avisarFamilias(); pintar(); }
      else if (G.st.como && !(ev.target.closest && ev.target.closest('.lf-como'))) { G.st.como = false; pintar(); }
      return;
    }
    if (b.matches('details summary *') && !b.dataset.acc) return;
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
    if (k === 'win') st.win = t.value === '' ? null : +t.value; else st[k] = t.value;
    if (k === 'gran' || k === 'op') st.per = null;
    pintar();
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
    if (ev.key === 'Escape' && G.st.menu) { G.st.menu = null; avisarFamilias(); pintar(); }
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.parte) return;
  if (data.parte === 'ficha') {
    if (!G.F || G.F.sello !== data.sello) { G.F = leerFicha(data); G.pan = null; }
  } else {
    let raiz = parentElement.querySelector('.cpv');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'lf cpv';
      parentElement.appendChild(raiz);
      enlazar(raiz);
      lfEscape(G, pintar);
      // La fecha y el filtro de Python siguen a su hueco si cambia el ancho.
      new ResizeObserver(() => lfPasarFecha(raiz, '.st-key-cp_prov_nativa_fecha')).observe(raiz);
    }
    G.raiz = raiz;
    G.enviar = setTriggerValue;
    if (G.rankData !== data) {
      G.rankData = data; G.R = leerRank(data);
      // Detalle docs. comparte esta selección; su fragment puede estar ya dibujado.
      window.dispatchEvent(new CustomEvent('compras-proveedores-cambio', {
        detail: { sel: data.sel || [], rango: data.rango, sello: data.sello }
      }));
    }
  }
  pintar();
}
