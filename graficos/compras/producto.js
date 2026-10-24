// Compras › Producto (regla #713).
//
// La monta graficos/compras/producto.py con st.components.v2 (sin iframe,
// estilos en un shadow root) DOS VECES, una en cada tarjeta: la del ranking
// (`parte: "rank"`, el resumen del rango) y la de la ficha (`parte:
// "ficha"`, el historial de líneas). Es la forma del boceto aprobado con
// sus cinco mejoras (https://claude.ai/artifact/1fymSPwVmqUtpQLnjzRB9m,
// página «Compras › Producto: pieza propia»). `_xlsx.js` va antepuesto
// (libro, bajar, archivo).
//
// UN CEREBRO, DOS MONTAJES. Sin iframe las dos piezas comparten `window`:
// `window.__cpProd` guarda los datos de las dos, el estado de lo elegido y
// las dos raíces, y dibuja cuando tiene las dos con la MISMA `sello`. El
// estado vive ahí y no en la raíz: sobrevive a que Streamlit vuelva a montar
// la pieza (cambiar de reporte y volver), como antes `session_state`.
//
// Nada vuelve a Python: buscar, «Ver por», familias, orden, el elegido, la
// ventana y el grano de la curva, las pestañas, el comprobante y el Excel
// los resuelve el navegador. Sólo la fecha del ranking (un botón de Python,
// arriba de la pieza) pide una corrida.
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
const VER = [['prod', 'Producto'], ['sub', 'Subfamilia'], ['fam', 'Familia']];
const GRANOS = [['Semana', 'Semana'], ['Mes', 'Mes'], ['Año', 'Año'], ['Documento', 'Doc.']];
const OPS = [['Rango', 'Rango de las tablas'], ['3m', 'Últimos 3 meses'], ['12m', 'Últimos 12 meses'],
  ['24m', 'Últimos 24 meses'], ['Todo', 'Todo el histórico']];
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
const fmtVar = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.05 ? '0.0%' : `${v > 0 ? '▲' : '▼'} ${Math.abs(v).toFixed(1)}%`);
// En el ranking: entero desde el 100 % (como el `_JS_VAR` del AgGrid de antes).
const fmtVarRk = (v) => (!finito(v) ? '—' : Math.abs(v) < 0.05 ? '0.0%'
  : `${v > 0 ? '▲' : '▼'} ${Math.abs(v) >= 100 ? Math.round(Math.abs(v)) : Math.abs(v).toFixed(1)}%`);
const clsVar = (v) => (!finito(v) || Math.abs(v) < 0.5 ? 'igual' : v > 0 ? 'sube' : 'baja');
const pctRk = (p) => `${p >= 10 || p === 0 ? Math.round(p) : p.toFixed(1)}%`;
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
  return { sello: data.sello, nombres: data.nombres, um: data.um, provs: data.provs, docs: data.docs, L,
    alto: data.alto_curva || 150, porDoc: null };
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

const G = window.__cpProd || (window.__cpProd = { st: {}, R: null, F: null, raices: {} });

// ── La lista ─────────────────────────────────────────────────────────────
function nomF(R, f) { return R.nomf[f] || f; }
function nomS(R, s) { return R.noms[s] || s; }

// Lo que muestra el ranking con el estado de hoy: filas, total, pie y el
// producto elegido (el de la ficha).
function lista() {
  const { R, F, st } = G;
  const ver = st.ver || 'prod';
  const fam = R.FAMS.some((f) => f.fam === st.fam) ? st.fam : null;
  const sub = ver === 'prod' && fam && R.SUBS.some((s) => s.fam === fam && s.sub === st.sub) ? st.sub : null;
  const q = st.q || '';
  const amb = R.P.filter((p) => (!fam || p.fam === fam) && (!sub || p.sub === sub));
  let vis = q ? amb.filter((p) => coincide(F.nombres[p.i], q)) : amb;
  if (st.soloRev) vis = vis.filter((p) => p.nflag > 0);
  const foco = vis.some((p) => p.i === st.foco) ? st.foco : null;
  const elegido = foco != null ? foco : (vis.length ? vis[0].i : (amb.length ? amb[0].i : (R.P[0] || {}).i));
  const filaSel = R.P.find((p) => p.i === elegido);
  let filas, total, ayudaPct;
  const base = (v) => v || 1;
  if (ver === 'prod') {
    const ambV = amb.reduce((s, p) => s + p.valor, 0);
    const max = Math.max(1, ...vis.map((p) => p.valor));
    ayudaPct = fam ? `% sobre ${sub ? nomS(R, sub) : nomF(R, fam)}` : '% sobre el total comprado en el rango';
    filas = vis.map((p) => ({ ...p, clave: p.i, nom: F.nombres[p.i], barra: p.valor / max, pct: p.valor / base(ambV) * 100,
      sel: p.i === elegido, marca: p.nflag > 0 }));
    let prevAmb = null;
    if (!q && !st.soloRev) {
      prevAmb = sub ? (R.SUBS.find((s) => s.fam === fam && s.sub === sub) || {}).prev
        : fam ? (R.FAMS.find((f) => f.fam === fam) || {}).prev : R.prevTotal;
    }
    const v = vis.reduce((s, p) => s + p.valor, 0), vr = vis.reduce((s, p) => s + p.vref, 0), rc = vis.reduce((s, p) => s + p.refc, 0);
    total = { nom: `Total · ${vis.length}${vis.length !== R.P.length ? ` de ${R.P.length}` : ''}`, valor: v,
      pct: v / base(ambV) * 100, var: varPct(v, prevAmb), hab: rc ? (vr / rc - 1) * 100 : null };
  } else {
    let rg, total0;
    if (ver === 'fam') {
      rg = R.FAMS.map((r) => ({ ...r, nom: nomF(R, r.fam), ayuda: nomF(R, r.fam), clave: r.fam }));
      total0 = R.P.reduce((s, p) => s + p.valor, 0);
      ayudaPct = '% sobre el total comprado en el rango';
    } else {
      rg = R.SUBS.filter((s) => !fam || s.fam === fam).sort((a, b) => b.valor - a.valor)
        .map((r) => ({ ...r, nom: nomS(R, r.sub), ayuda: `${nomS(R, r.sub)} · ${nomF(R, r.fam)}`, clave: `${r.fam}\u001f${r.sub}` }));
      total0 = fam ? (R.FAMS.find((f) => f.fam === fam) || {}).valor : R.P.reduce((s, p) => s + p.valor, 0);
      ayudaPct = fam ? `% sobre ${nomF(R, fam)}` : '% sobre el total comprado en el rango';
    }
    if (q) rg = rg.filter((r) => coincide(r.nom, q));
    const max = Math.max(1, ...rg.map((r) => r.valor));
    filas = rg.map((r) => ({ ...r, barra: r.valor / max, pct: r.valor / base(total0) * 100,
      sel: filaSel && (ver === 'fam' ? r.fam === filaSel.fam : r.fam === filaSel.fam && r.sub === filaSel.sub) }));
    const v = rg.reduce((s, r) => s + r.valor, 0), vr = rg.reduce((s, r) => s + r.vref, 0), rc = rg.reduce((s, r) => s + r.refc, 0);
    total = { nom: `Total · ${rg.length}`, valor: v, pct: v / base(total0) * 100, n: rg.reduce((s, r) => s + r.n, 0),
      var: q ? null : varPct(v, rg.reduce((s, r) => s + r.prev, 0)), hab: rc ? (vr / rc - 1) * 100 : null };
  }
  const s = st.sort;
  if (s) {
    const k = { nom: (r) => sinTildes(r.nom), val: (r) => r.valor, pct: (r) => r.valor, n: (r) => r.n,
      var: (r) => (r.est ? (s.dir > 0 ? 1e15 : -1e15) : finito(r.var) ? r.var : -1e16), hab: (r) => (finito(r.hab) ? r.hab : -1e16) }[s.col];
    if (k) filas.sort((a, b) => { const x = k(a), y = k(b); return (x < y ? -1 : x > y ? 1 : 0) * s.dir; });
  }
  return { ver, fam, sub, q, filas, total, ayudaPct, elegido };
}

// La mini-curva de 12 meses de un producto: el precio ponderado de cada mes.
function spark(i) {
  const cache = G.spark || (G.spark = new Map());
  if (cache.has(i)) return cache.get(i);
  const { R, F } = G;
  const ini = restarMeses(R.ULT, 12) + 1, keys = secuencia(inicioDe(ini, 'Mes'), R.ULT, 'Mes');
  const ag = new Map(keys.map((k) => [k, { pc: 0, pv: 0 }]));
  F.L[i].forEach((l) => {
    if (l.d < ini || l.flag || l.cant <= 0) return;
    const a = ag.get(clave(l.d, 'Mes'));
    if (a) { a.pc += l.cant; a.pv += l.valor; }
  });
  const ps = keys.map((k) => { const a = ag.get(k); return a.pc > 0 ? a.pv / a.pc : null; });
  const vs = ps.filter(finito);
  let pts = '';
  if (vs.length > 1) {
    const lo = Math.min(...vs), hi = Math.max(...vs), r = hi - lo || hi * 0.1 || 1;
    pts = ps.map((p, j) => (finito(p) ? `${(1 + j * 38 / (keys.length - 1)).toFixed(1)},${(14 - (p - lo) / r * 12).toFixed(1)}` : null))
      .filter(Boolean).join(' ');
  }
  cache.set(i, pts);
  return pts;
}

function pintarRank() {
  const raiz = G.raices.rank;
  if (!raiz) return;
  const { R, F, st } = G;
  const v = lista();
  G.vista = v;
  const conN = v.ver !== 'prod', conSpark = v.ver === 'prod';
  raiz.style.setProperty('--cpr-cols', `minmax(0, 1fr) ${conSpark ? '78px 38px' : '88px 42px'}${conN ? ' 40px' : ''} ${conSpark ? '58px 56px 40px' : '62px 58px'}`);
  const busca = raiz.querySelector('.busca');
  if (busca && busca !== raiz.getRootNode().activeElement && busca.value !== (st.q || '')) busca.value = st.q || '';
  raiz.querySelectorAll('[data-acc="ver"]').forEach((b) => b.classList.toggle('on', b.dataset.v === v.ver));
  const rev = raiz.querySelector('[data-acc="rev"]');
  rev.classList.toggle('on', !!st.soloRev);
  rev.innerHTML = `<span class="w">⚠</span> Sólo las que tienen algo para revisar · ${R.nflag}`;
  // Familias y subfamilias.
  const pill = (acc, val, txt, on) => `<button class="pill${on ? ' on' : ''}" data-acc="${acc}" data-v="${esc(val)}">${esc(txt)}</button>`;
  raiz.querySelector('.fams').innerHTML = v.ver === 'fam' ? ''
    : pill('fam', '', 'Todas', !v.fam) + R.FAMS.map((f) => pill('fam', f.fam, nomF(R, f.fam), v.fam === f.fam)).join('');
  const subs = v.ver === 'prod' && v.fam ? R.SUBS.filter((s) => s.fam === v.fam) : [];
  raiz.querySelector('.subs').innerHTML = subs.length
    ? pill('sub', '', 'Todas', !v.sub) + subs.map((s) => pill('sub', s.sub, nomS(R, s.sub), v.sub === s.sub)).join('') : '';
  // La tabla.
  const col = st.sort && st.sort.col, dir = st.sort && st.sort.dir;
  const cab = [['nom', VER.find((x) => x[0] === v.ver)[1], '', 'i'], ['val', 'Valor', '', 'r'], ['pct', '%', v.ayudaPct, 'r']];
  if (conN) cab.push(['n', 'Prod.', 'Productos distintos comprados', 'r']);
  cab.push(['var', 'Δ', 'El valor contra el período anterior de igual largo', 'r'],
    ['hab', 'vs. hab.', 'El precio pagado contra el habitual (la mediana de los 90 días anteriores), sin las compras marcadas', 'r']);
  let html = '<div class="rk-f rk-h">' + cab.map(([k, t, ayuda, al]) =>
    `<button class="${al}" data-acc="orden" data-v="${k}" title="${esc(ayuda)}">${esc(t)}${col === k ? (dir > 0 ? ' ↑' : ' ↓') : ''}</button>`).join('')
    + (conSpark ? '<span class="c" title="El precio ponderado de cada mes, últimos 12 meses">12 m</span>' : '') + '</div><div class="rk-l">';
  html += v.filas.map((f) => {
    const nom = (f.marca ? '⚠ ' : '') + f.nom;
    const ayuda = v.ver === 'prod' ? f.nom + (f.marca ? ' · tiene una compra para revisar' : '') : f.ayuda;
    const varTxt = f.est || fmtVarRk(f.var);
    const varCls = f.est === 'nuevo' ? 'nuevo' : f.est === 'vuelve' ? 'vuelve' : clsVar(f.var);
    const varAy = f.est === 'nuevo' ? 'Primera compra en este rango' : f.est === 'vuelve' ? 'No se compró en el período anterior' : '';
    return `<div class="rk-f${f.sel ? ' sel' : ''}" data-acc="fila" data-v="${esc(f.clave)}" title="${esc(ayuda)}">`
      + `<span class="nm">${esc(nom)}</span>`
      + `<span class="r val" style="--b:${(Math.max(0, Math.min(1, f.barra)) * 100).toFixed(1)}%">${soles(f.valor)}</span>`
      + `<span class="r">${pctRk(Math.round(f.pct * 10) / 10)}</span>`
      + (conN ? `<span class="r">${f.n}</span>` : '')
      + `<span class="r b ${varCls}" title="${esc(varAy)}">${esc(varTxt)}</span>`
      + `<span class="r b ${clsVar(f.hab)}">${fmtVar(f.hab)}</span>`
      + (conSpark ? `<svg class="sp" viewBox="0 0 40 16" preserveAspectRatio="none" aria-hidden="true"><polyline points="${spark(f.i)}"/></svg>` : '')
      + '</div>';
  }).join('');
  if (!v.filas.length) html += '<div class="vacio">Nada con ese filtro.</div>';
  const t = v.total;
  html += '</div><div class="rk-f rk-t">'
    + `<span class="nm">${esc(t.nom)}</span><span class="r">${soles(t.valor)}</span><span class="r">${pctRk(Math.round(t.pct * 10) / 10)}</span>`
    + (conN ? `<span class="r">${t.n ?? ''}</span>` : '')
    + `<span class="r ${clsVar(t.var)}">${fmtVarRk(t.var)}</span><span class="r ${clsVar(t.hab)}">${fmtVar(t.hab)}</span>`
    + (conSpark ? '<span></span>' : '') + '</div>';
  raiz.querySelector('.tabla').innerHTML = html;
  raiz.querySelector('.pie').textContent = v.ver === 'prod'
    ? `${R.n80} productos hacen el 80 % de lo comprado · ⚠ ${R.nflag} con una compra para revisar`
    : `Clic en una ${v.ver === 'fam' ? 'familia' : 'subfamilia'}: sus productos · Δ contra el período anterior`;
  const sel = raiz.querySelector('.rk-f.sel');
  if (sel && G.scrollAlSel) { sel.scrollIntoView({ block: 'nearest' }); G.scrollAlSel = false; }
}

function excel() {
  const { R } = G;
  const v = G.vista || lista();
  let cab, filas;
  if (v.ver === 'prod') {
    cab = ['Producto', 'Familia', 'Subfamilia', 'Unidad', 'Valor (S/)', 'Cantidad', '% del ámbito', 'Δ % vs. período anterior',
      'Estado', 'Precio ponderado (S/)', 'vs. precio habitual %', 'Impacto del precio (S/)', 'Compras', 'Líneas para revisar'];
    filas = v.filas.map((f) => [f.nom, nomF(R, f.fam), nomS(R, f.sub), f.um, f.valor, f.cant, f.pct, f.var, f.est,
      f.pp, f.hab, f.ppv, f.docs, f.nflag]);
  } else {
    cab = [v.ver === 'fam' ? 'Familia' : 'Subfamilia', ...(v.ver === 'sub' ? ['Familia'] : []), 'Valor (S/)', '% del ámbito',
      'Productos', 'Δ % vs. período anterior', 'Estado', 'vs. precio habitual %', 'Productos con algo para revisar'];
    filas = v.filas.map((f) => [f.nom, ...(v.ver === 'sub' ? [nomF(R, f.fam)] : []), f.valor, f.pct, f.n, f.var, f.est, f.hab, f.nflag]);
  }
  const nombre = `compras_producto_${archivo(VER.find((x) => x[0] === v.ver)[1])}_${iso(R.R0)}_${iso(R.R1)}.xlsx`;
  bajar(nombre, libro([{ nombre: `Ranking por ${VER.find((x) => x[0] === v.ver)[1].toLowerCase()}`, cabeza: cab, filas }]));
}

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
    if (rows.length > 1 && min != null && a.p === min) dif = celda('<i class="chip barato">más barato</i>', 'r');
    else if (rows.length > 1 && finito(a.p) && min) { const x = (a.p / min - 1) * 100; dif = celda(`+${x.toFixed(1)}%`, `r${x > 10 ? ' sube' : ''}`); }
    else dif = celda('—', 'r igual');
    return `<div class="ft-f" data-acc="prov" data-v="${a.prov}" title="Clic: sus compras">`
      + celda(esc(F.provs[a.prov]) + (a.fl ? ' <i class="w" title="Incluye una compra para revisar">⚠</i>' : ''), 'nm')
      + celda(cant(a.c, um), 'r') + celda(precio(a.p), 'r') + dif + celda(soles(a.v), 'r')
      + celda(`${Math.round(a.v / tot * 100)}%`, 'r gr') + celda(fCorta(a.ult), 'r gr') + '</div>';
  });
  const pc = rows.reduce((s, a) => s + a.pc, 0), pv = rows.reduce((s, a) => s + a.pv, 0);
  const c = rows.reduce((s, a) => s + a.c, 0), v = rows.reduce((s, a) => s + a.v, 0);
  return { n: rows.length, html: tabla('pv',
    [celda('Proveedor'), celda('Cant.', 'r'), celda('Precio', 'r'), celda('vs. más barato', 'r', 'Cuánto más caro sale que el más barato, en los mismos días'),
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
    const acc = a.sinDoc ? '' : ` data-acc="doc" data-v="${a.doc}|${a.d}|${a.prov}" title="Clic: el comprobante entero"`;
    return `<div class="ft-f"${acc}>` + celda(fCorta(a.d)) + celda(esc(F.provs[a.prov]), 'nm')
      + celda(esc(F.docs[a.doc] || '—'), 'nm gr') + celda(cant(a.cant), 'r') + celda(precio(pu), 'r')
      + celda(fmtVar(h), `r b ${clsVar(h)}`) + celda(soles(a.valor), 'r')
      + (a.flag ? celda('<i class="chip revisar">revisar</i>', 'r', ayudaMarca(a, um)) : celda('')) + '</div>';
  });
  return { n: D.length, html: tabla('cp',
    [celda('Fecha'), celda('Proveedor'), celda('Documento'), celda('Cant.', 'r'), celda('Precio', 'r'),
      celda('vs. hab.', 'r', 'El precio de esa compra contra el habitual de ese día'), celda('Valor', 'r'), celda('')],
    filas,
    [celda(`Total · ${D.length} ${D.length === 1 ? 'compra' : 'compras'}`, 'nm tot3'), celda(cant(D.reduce((s, a) => s + a.cant, 0), um), 'r'),
      celda(precio(pc ? pv / pc : null) + (D.some((a) => a.flag) ? ' <i class="w" title="Sin las compras marcadas para revisar">⚠</i>' : ''), 'r'),
      celda(fmtVar(ph), `r ${clsVar(ph)}`), celda(soles(D.reduce((s, a) => s + a.valor, 0)), 'r'), celda('')]) };
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
    return `<div class="ft-f${k === sel ? ' sel' : ''}" data-acc="per" data-v="${esc(k)}" title="Clic: sus compras">`
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
    [celda('Período'), celda('Cant.', 'r'), celda('Precio', 'r'), celda('vs. hab.', 'r'), celda('Valor', 'r'),
      celda('%', 'r', '% del valor de la curva'), celda('Docs', 'r'), celda('Δ precio', 'r', 'El precio contra el período anterior')],
    filas,
    [celda('Total', 'nm'), celda(cant(S.agg.reduce((s, a) => s + a.c, 0), um), 'r'), celda(precio(pc ? pv / pc : null), 'r'),
      celda(fmtVar(ph), `r ${clsVar(ph)}`), celda(soles(tot), 'r'), celda('100%', 'r'), celda(String(S.agg.reduce((s, a) => s + a.docs, 0)), 'r'), celda('')]);
}

// La curva: cantidad en barras, precio ponderado en línea y el habitual
// punteado (la `_fig_producto` de antes, sin Plotly).
function curva(S, gran, um, per, ancho, alto) {
  const { F } = G;
  const W = Math.max(280, ancho), PL = 44, PR = 52, PT = 8, PB = 22, PH = alto - PT - PB;
  const n = S.keys.length, slot = (W - PL - PR) / n;
  const cants = S.agg.map((a) => a.c);
  const ymax = Math.max(...cants, S.refq || 0, 0) * 1.18 || 1;
  const pr = S.agg.map(precioDe), hb = S.agg.map(habDe);
  // El eje del precio: con un mínimo de alto (8 % del máximo), si no una
  // variación de 0,4 % se dibujaba como una montaña.
  const nums = pr.concat(hb).filter(finito);
  let y2 = [0, 1];
  if (nums.length) {
    const lo = Math.min(...nums), hi = Math.max(...nums), pad = (hi - lo) * 0.18, mn = hi * 0.08 || 1;
    if (hi - lo + 2 * pad < mn) { const mid = (hi + lo) / 2; y2 = [Math.max(0, mid - mn / 2), mid + mn / 2]; } else y2 = [Math.max(0, lo - pad), hi + pad];
  }
  const X = (i) => PL + (i + 0.5) * slot, Y = (c) => PT + PH - c / ymax * PH, Y2 = (p) => PT + PH - (p - y2[0]) / (y2[1] - y2[0]) * PH;
  const parc = !!S.parc, bw = Math.max(1.5, slot * 0.65);
  const redondo = (r) => { const b = Math.pow(10, Math.floor(Math.log10(r || 1))); const f = r / b; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * b; };
  const fmtY = (v) => (v >= 1000 ? `${+(v / 1000).toFixed(1)}k` : String(+v.toFixed(1)));
  let svg = `<svg width="${W}" height="${alto}" viewBox="0 0 ${W} ${alto}" role="img" aria-label="Cantidad y precio por período">`
    + '<defs><pattern id="cpf-raya" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    + '<rect width="6" height="6" class="rb"/><line x1="0" y1="0" x2="0" y2="6" class="rl"/></pattern></defs>';
  const pc = redondo(ymax / 1.18 / 2);
  for (let v = 0; v <= ymax * 0.98; v += pc) {
    svg += `<line class="gr" x1="${PL}" x2="${W - PR}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/>`
      + `<text class="ty" x="${PL - 6}" y="${(Y(v) + 3.5).toFixed(1)}" text-anchor="end">${fmtY(v)}${um ? ' ' + esc(um) : ''}</text>`;
  }
  const pp = redondo((y2[1] - y2[0]) / 2);
  for (let v = Math.ceil(y2[0] / pp) * pp; v <= y2[1]; v += pp) {
    svg += `<text class="t2" x="${W - PR + 6}" y="${(Y2(v) + 3.5).toFixed(1)}">S/ ${pp >= 1 ? ent(v) : v.toFixed(pp >= 0.1 ? 1 : 2)}</text>`;
  }
  S.keys.forEach((k, i) => {
    const a = S.agg[i], h = Math.max(0, a.c / ymax * PH);
    const cls = per ? (k === per ? 'b on' : 'b off') : 'b';
    svg += `<rect class="${cls}" x="${(X(i) - bw / 2).toFixed(1)}" y="${(PT + PH - h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="2"/>`;
    if (parc && i === n - 1) svg += `<rect class="raya" x="${(X(i) - bw / 2).toFixed(1)}" y="${(PT + PH - h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" fill="url(#cpf-raya)"/>`;
  });
  const ult = parc ? n - 2 : n - 1;
  const linea = (vals, hasta) => vals.slice(0, hasta + 1).map((p, i) => (finito(p) ? `${X(i).toFixed(1)},${Y2(p).toFixed(1)}` : null)).filter(Boolean).join(' ');
  svg += `<polyline class="hab" points="${linea(hb, n - 1)}"/><polyline class="pr" points="${linea(pr, ult)}"/>`;
  pr.slice(0, ult + 1).forEach((p, i) => { if (finito(p)) svg += `<circle class="pr" cx="${X(i).toFixed(1)}" cy="${Y2(p).toFixed(1)}" r="2.5"/>`; });
  if (parc && n > 1 && finito(pr[n - 1])) {
    let k = -1;
    for (let i = n - 2; i >= 0; i -= 1) if (finito(pr[i])) { k = i; break; }
    if (k >= 0) svg += `<polyline class="prp" points="${X(k).toFixed(1)},${Y2(pr[k]).toFixed(1)} ${X(n - 1).toFixed(1)},${Y2(pr[n - 1]).toFixed(1)}"/>`;
    svg += `<circle class="pra" cx="${X(n - 1).toFixed(1)}" cy="${Y2(pr[n - 1]).toFixed(1)}" r="4.5"/>`;
  }
  if (parc && S.refq) svg += `<line class="ref" x1="${(X(n - 1) - 13).toFixed(1)}" x2="${(X(n - 1) + 13).toFixed(1)}" y1="${Y(S.refq).toFixed(1)}" y2="${Y(S.refq).toFixed(1)}"/>`;
  S.agg.forEach((a, i) => {
    if (!a.fl) return;
    let y;
    if (finito(pr[i])) y = Y2(pr[i]);
    else if (a.c > 0) y = Y2(Math.min(Math.max(a.v / a.c, y2[0]), y2[1]));
    else return;
    svg += `<circle class="fl" cx="${X(i).toFixed(1)}" cy="${y.toFixed(1)}" r="4"/>`;
  });
  const etqs = S.keys.map((k) => etq(k, gran, false, F)), largo = Math.max(1, ...etqs.map((e) => e.length));
  const paso = Math.max(1, Math.ceil(n / Math.max(1, Math.floor((W - PL - PR) / (largo * 6.6 + 10)))));
  S.keys.forEach((k, i) => {
    if ((n - 1 - i) % paso === 0) svg += `<text class="tx" x="${X(i).toFixed(1)}" y="${alto - 6}" text-anchor="middle">${esc(etqs[i])}</text>`;
  });
  // La zona de cada período, a toda la altura: el cursor y el clic.
  S.keys.forEach((k, i) => {
    svg += `<rect class="hit" data-acc="barra" data-v="${esc(k)}" x="${(PL + i * slot).toFixed(1)}" y="${PT}" width="${slot.toFixed(1)}" height="${PH}"></rect>`;
  });
  svg += '</svg>';
  return { svg, X, W };
}

function ficha() {
  const { R, F, st } = G;
  const v = G.vista || lista();
  const fila = R.P.find((p) => p.i === v.elegido);
  if (!fila) return { html: '<div class="nota-v">Sin productos en el rango.</div>' };
  const um = fila.um || '', h = F.L[fila.i], nom = F.nombres[fila.i];
  const gran = st.gran || 'Mes', op = st.op || '3m', tab = st.tab || 'prov', pw = st.pw || '90';
  // Subtítulo y cifras del rango.
  const subt = [nomS(R, fila.sub), nomF(R, fila.fam)];
  if (fila.ult != null) {
    let u = `última compra ${fCorta(fila.ult)}`;
    if (finito(fila.ultp)) u += ` a ${precio(fila.ultp)} / ${um || 'unidad'}`;
    if (finito(fila.cada)) { const c = Math.round(fila.cada); u += `, cada ${c} ${c === 1 ? 'día' : 'días'}`; }
    subt.push(u);
  }
  subt.push(`${fila.docs} ${fila.docs === 1 ? 'compra' : 'compras'} en el rango`);
  const ant = `${fCorta(R.R0 - R.DIAS)} – ${fCorta(R.R0 - 1)}`;
  const kpi = (rot, val, cls, sub, ayuda, extra) => `<div class="kpi"${ayuda ? ` title="${esc(ayuda)}"` : ''}><span>${esc(rot)}</span>`
    + `<p><b class="${cls || ''}">${val}</b>${sub ? `<small>${esc(sub)}</small>` : ''}${extra || ''}</p></div>`;
  let kVar;
  if (fila.est) {
    kVar = kpi(`vs. los ${R.DIAS} días antes`, `<i class="chip ${fila.est}">${fila.est}</i>`, '', '',
      `${ant} · ${fila.est === 'nuevo' ? 'Primera compra de este producto' : 'No se compró en el período anterior'}`);
  } else kVar = kpi(`vs. los ${R.DIAS} días antes`, fmtVar(fila.var), clsVar(fila.var), '', ant);
  let kPpv;
  if (!finito(fila.ppv)) kPpv = kpi('Impacto del precio', '—', 'igual');
  else if (Math.abs(fila.ppv) < 1) kPpv = kpi('Impacto del precio', 'S/ 0', 'igual');
  else {
    kPpv = kpi('Impacto del precio', `${fila.ppv > 0 ? '+' : '−'}S/ ${ent(Math.abs(fila.ppv))}`, fila.ppv > 0 ? 'sube' : 'baja',
      fila.ppv > 0 ? 'de más' : 'de ahorro',
      '(precio pagado − precio habitual) × cantidad, sobre las compras del rango: la variación de precio de compra de la contabilidad de costos estándar');
  }
  const kpis = kpi('Compra en el rango', soles(fila.valor), '', cant(fila.cant, um)) + kVar
    + kpi('Precio ponderado', precio(fila.pp), '', `/ ${um || 'unidad'}`, '',
      fila.nflag ? '<i class="w" title="Sin las compras marcadas para revisar">⚠</i>' : '')
    + kpi('vs. precio habitual', fmtVar(fila.hab), clsVar(fila.hab), '',
      'El precio pagado en el rango contra el habitual de cada compra: la mediana de los 90 días anteriores, la misma de «Compras por período» y de Proveedor')
    + kPpv;
  // La curva.
  const S = serie(h, gran, op, R.ULT, [R.R0, R.R1]);
  const per = S && S.keys.includes(st.per) ? st.per : null;
  G.S = S; G.gran = gran; G.um = um;
  let curvaHtml, leyHtml = '';
  if (!S) {
    curvaHtml = `<div class="sin-curva">Sin compras de este producto en «${op === 'Rango' ? 'el rango' : OPS.find((o) => o[0] === op)[1].toLowerCase()}».</div>`;
  } else {
    const ancho = (G.raices.ficha && G.raices.ficha.clientWidth) || 700;
    const c = curva(S, gran, um, per, ancho, F.alto);
    G.X = c.X; G.W = c.W;
    curvaHtml = `<div class="curva" style="height:${F.alto}px">${c.svg}<div class="tip" hidden></div></div>`;
    const ley = [`<span><i class="m bar"></i>${esc(um || 'unidades')} comprados</span>`, '<span><i class="m lin"></i>precio ponderado</span>',
      '<span><i class="m hab"></i>precio habitual</span>'];
    if (S.agg.some((a) => a.fl)) ley.push('<span><i class="m fl"></i>con compras para revisar</span>');
    const n = S.keys.length;
    if (S.parc && (S.agg[n - 1].c || S.refq)) {
      const vv = varPct(S.agg[n - 1].c, S.refq);
      ley.push(`<span>${esc(S.parc.rot)}: ${esc(cant(S.agg[n - 1].c, um))} · <i class="m raya"></i>${esc(S.parc.rotRef)}: `
        + `${esc(cant(S.refq, um))} <b class="${clsVar(vv)}">${fmtVar(vv)}</b></span>`);
    }
    leyHtml = `<div class="ley">${ley.join('')}</div>`;
  }
  // Los ámbitos de las pestañas (los de `_ficha` de antes).
  const cprov = h.some((l) => l.prov === st.cprov) ? st.cprov : null;
  const lin = S ? S.lineas : [];
  const bsel = per ? lin.filter((l) => l.k === per) : null;
  let Lp;
  if (pw === 'ven') Lp = bsel || lin;
  else { const p0 = pw === 'rango' ? R.R0 : R.R1 - 89; Lp = h.filter((l) => l.d >= p0 && l.d <= R.R1); }
  let Lc = bsel || (cprov != null ? Lp : h.filter((l) => l.d >= R.R0 && l.d <= R.R1));
  if (cprov != null) Lc = Lc.filter((l) => l.prov === cprov);
  const tPv = tablaProveedores(Lp, um), tCp = tablaCompras(Lc, um);
  const tabs = [['prov', `Proveedores · ${tPv.n}`], ['comp', `Compras · ${tCp.n}`], ['per', `Períodos · ${S ? S.keys.length : 0}`]]
    .map(([k, t]) => `<button class="tab${k === tab ? ' on' : ''}" data-acc="tab" data-v="${k}">${esc(t)}</button>`).join('');
  let der = '';
  if (tab === 'prov') {
    const ven = per ? etq(per, gran, true, F) : 'La curva';
    der = '<span class="nota">comparar en</span>' + [['rango', 'El rango'], ['90', '90 días'], ['ven', ven]]
      .map(([k, t]) => `<button class="pw${k === pw ? ' on' : ''}" data-acc="pw" data-v="${k}">${esc(t)}</button>`).join('');
  } else if (tab === 'comp') {
    if (per || cprov != null) {
      const t = [per ? etq(per, gran, true, F) : '', cprov != null ? F.provs[cprov] : '',
        per || cprov == null ? '' : { rango: 'el rango', 90: '90 días', ven: 'la curva' }[pw]].filter(Boolean).join(' · ');
      der = `<button class="soltar" data-acc="soltar" title="Volver a las compras del rango">${esc(trunc(t, 46))} ✕</button>`;
    } else der = '<span class="nota">del rango · clic en una barra: ese período · clic en una compra: su comprobante</span>';
  } else der = '<span class="nota">una fila por barra de la curva · clic: sus compras</span>';
  const cuerpo = tab === 'prov' ? tPv.html : tab === 'comp' ? tCp.html : (S ? tablaPeriodos(S, gran, um, per) : '<div class="nota-v">Sin curva.</div>');
  const opRot = OPS.find((o) => o[0] === op)[1];
  const html = '<div class="cab">'
    + `<h3 title="${esc(nom)}">${esc(nom)}</h3>`
    + `<div class="ven"><button class="ven-b" data-acc="ven-abrir" aria-haspopup="listbox" aria-expanded="${st.opAbierto ? 'true' : 'false'}">${esc(opRot)} <i>▾</i></button>`
    + (st.opAbierto ? `<div class="ven-l" role="listbox">${OPS.map(([k, t]) => `<button role="option" class="${k === op ? 'on' : ''}" data-acc="op" data-v="${k}">${esc(t)}</button>`).join('')}</div>` : '')
    + '</div>'
    + `<div class="seg">${GRANOS.map(([k, t]) => `<button class="${k === gran ? 'on' : ''}" data-acc="gran" data-v="${k}">${t}</button>`).join('')}</div>`
    + '</div>'
    + `<p class="sub" title="${esc(subt.join(' · '))}">${esc(subt.join(' · '))}</p>`
    + `<div class="kpis">${kpis}</div>` + curvaHtml + leyHtml
    + `<div class="tabs">${tabs}<span class="esp"></span>${der}</div>`
    + `<div class="cuerpo">${cuerpo}</div>` + comprobante();
  return { html };
}

// El comprobante entero de una compra: sus líneas de TODOS los productos.
function comprobante() {
  const { F, st } = G;
  if (!st.doc) return '';
  const [doc, d, prov] = st.doc.split('|').map(Number);
  const ls = (porDoc(F).get(`${doc}|${d}|${prov}`) || []).slice().sort((a, b) => b.valor - a.valor);
  const tot = ls.reduce((s, l) => s + l.valor, 0);
  const elegido = (G.vista || {}).elegido;
  return '<div class="doc" role="dialog" aria-label="Comprobante">'
    + `<div class="doc-c"><b>${esc(F.docs[doc] || 'Comprobante')}</b><span class="esp"></span><button data-acc="doc-cerrar" aria-label="Cerrar">✕</button></div>`
    + `<p class="doc-s">${esc(F.provs[prov])} · ${fCorta(d)} · ${ls.length} ${ls.length === 1 ? 'línea' : 'líneas'}</p>`
    + '<div class="doc-f doc-h"><span>Producto</span><span class="r">Cant.</span><span class="r">Precio</span><span class="r">Valor</span></div>'
    + '<div class="doc-l">' + ls.map((l) => `<div class="doc-f${l.prod === elegido ? ' sel' : ''}">`
      + `<span class="nm" title="${esc(F.nombres[l.prod])}">${esc(F.nombres[l.prod])}${l.flag ? ' <i class="w">⚠</i>' : ''}</span>`
      + `<span class="r">${cant(l.cant, F.um[l.prod])}</span><span class="r">${precio(l.cant ? l.valor / l.cant : null)}</span>`
      + `<span class="r">${soles(l.valor)}</span></div>`).join('') + '</div>'
    + `<div class="doc-f doc-t"><span>Total del comprobante</span><span></span><span></span><span class="r">${soles(tot)}</span></div>`
    + '<p class="doc-n">Las líneas de los productos de las familias que dejan ver los filtros del reporte.</p></div>';
}

function pintarFicha() {
  const raiz = G.raices.ficha;
  if (!raiz) return;
  const scroll = raiz.querySelector('.ft-l');
  const y = scroll ? scroll.scrollTop : 0;
  const mismo = G.fichaDe === `${(G.vista || {}).elegido}|${G.st.tab}`;
  raiz.innerHTML = ficha().html;
  G.fichaDe = `${(G.vista || {}).elegido}|${G.st.tab}`;
  const nuevo = raiz.querySelector('.ft-l');
  if (nuevo && mismo) nuevo.scrollTop = y;
}

// La ficha al pasar el cursor por un período: la de siempre y sus compras.
function pintarTip(k) {
  const raiz = G.raices.ficha;
  const tip = raiz && raiz.querySelector('.tip');
  const S = G.S;
  if (!tip || !S) return;
  const i = k == null ? -1 : S.keys.indexOf(k);
  if (i < 0) { tip.hidden = true; return; }
  const { F } = G, um = G.um, gran = G.gran;
  const a = S.agg[i], p = precioDe(a), parc = S.parc && i === S.keys.length - 1;
  let html = `<b>${esc(etq(k, gran, true, F))}${parc ? ' (en curso)' : ''}</b>`
    + `<div>${esc(cant(a.c, um))}${finito(p) ? ` · ${precio(p)} por ${esc(um || 'unidad')}` : ''}</div>`
    + `<div>${soles(a.v)} · ${a.docs} ${a.docs === 1 ? 'compra' : 'compras'}</div>`;
  if (a.fl) html += `<div class="tw">${a.fl} para revisar, fuera del precio</div>`;
  const ds = porDocumento(S.lineas.filter((l) => l.k === k)).sort((x, y) => y.d - x.d);
  if (ds.length) {
    html += '<div class="tc">Sus compras</div>' + ds.slice(0, FILAS_TIP).map((x) => `<div class="tl">${fCorta(x.d)} · `
      + `${esc(trunc(F.provs[x.prov], 20))} · ${esc(cant(x.cant))} · ${precio(x.cant ? x.valor / x.cant : null)}${x.flag ? ' ⚠' : ''}</div>`).join('');
    if (ds.length > FILAS_TIP) html += `<div class="tm">y ${ds.length - FILAS_TIP} más · clic: todas</div>`;
    else html += '<div class="tm">clic: sus compras abajo</div>';
  }
  tip.innerHTML = html;
  tip.hidden = false;
  const tw = tip.offsetWidth || 280, x = G.X(i);
  tip.style.left = `${x + 14 + tw <= G.W ? x + 14 : Math.max(0, x - 14 - tw)}px`;
}

function pintar() {
  const { R, F } = G;
  if (!R || !F || R.sello !== F.sello) {
    if (G.raices.ficha && !G.raices.ficha.innerHTML) G.raices.ficha.innerHTML = '<div class="nota-v">Cargando…</div>';
    return;
  }
  pintarRank();
  pintarFicha();
}

// ── Los clics ────────────────────────────────────────────────────────────
function accion(acc, val) {
  const st = G.st;
  if (acc === 'buscar') return;
  if (acc !== 'ven-abrir') st.opAbierto = false;
  if (acc === 'ver') {
    st.ver = val; st.sort = null;
    if (val === 'fam') { st.fam = null; st.sub = null; } else if (val === 'sub') st.sub = null;
  } else if (acc === 'rev') { st.soloRev = !st.soloRev; st.foco = null; }
  else if (acc === 'excel') { excel(); return; }
  else if (acc === 'fam') { st.fam = val || null; st.sub = null; st.foco = null; }
  else if (acc === 'sub') { st.sub = val || null; st.foco = null; }
  else if (acc === 'orden') {
    const s = st.sort;
    st.sort = !s || s.col !== val ? { col: val, dir: val === 'nom' ? 1 : -1 } : s.dir === (val === 'nom' ? 1 : -1) ? { col: val, dir: -s.dir } : null;
  } else if (acc === 'fila') {
    const v = G.vista;
    if (v.ver === 'prod') { const i = +val; st.foco = st.foco === i ? null : i; st.per = null; st.cprov = null; st.doc = null; }
    else {
      const [fam, sub] = val.split('\u001f');
      Object.assign(st, { ver: 'prod', fam, sub: sub || null, q: '', foco: null, per: null, cprov: null, sort: null, doc: null });
      G.scrollAlSel = true;
    }
  } else if (acc === 'ven-abrir') { st.opAbierto = !st.opAbierto; pintarFicha(); return; }
  else if (acc === 'op') { st.op = val; st.per = null; st.opAbierto = false; }
  else if (acc === 'gran') { st.gran = val; st.per = null; }
  else if (acc === 'barra') {
    st.per = st.per === val ? null : val; st.cprov = null;
    if ((st.tab || 'prov') === 'prov') st.pw = 'ven'; else st.tab = 'comp';
  } else if (acc === 'tab') st.tab = val;
  else if (acc === 'pw') st.pw = val;
  else if (acc === 'prov') { st.cprov = +val; st.tab = 'comp'; if ((st.pw || '90') !== 'ven') st.per = null; }
  else if (acc === 'per') { st.per = st.per === val ? null : val; st.cprov = null; st.tab = 'comp'; }
  else if (acc === 'soltar') { st.per = null; st.cprov = null; }
  else if (acc === 'doc') { st.doc = val; pintarFicha(); return; }
  else if (acc === 'doc-cerrar') { st.doc = null; pintarFicha(); return; }
  else return;
  pintar();
}
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b)) {
      if (G.st.opAbierto) { G.st.opAbierto = false; pintarFicha(); }
      return;
    }
    accion(b.dataset.acc, b.dataset.v);
  });
  raiz.addEventListener('input', (ev) => {
    if (!ev.target.classList.contains('busca')) return;
    G.st.q = ev.target.value; G.st.foco = null;
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
    if (ev.key === 'Escape' && G.st.doc) { G.st.doc = null; pintarFicha(); }
  });
}

const ESQ_RANK = '<div class="ctl"><label class="lb"><span>Buscar</span><input class="busca" type="search" placeholder="Buscar…" autocomplete="off"></label>'
  + `<div class="seg" role="group" aria-label="Ver por">${VER.map(([k, t]) => `<button data-acc="ver" data-v="${k}">${t}</button>`).join('')}</div></div>`
  + '<div class="rev"><button class="pill" data-acc="rev"></button><span class="esp"></span><button class="excel" data-acc="excel" title="Baja la tabla tal como se ve">Excel</button></div>'
  + '<div class="fams"></div><div class="subs"></div><div class="tabla"></div><p class="pie"></p>';

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.parte) return;
  if (data.parte === 'ficha') {
    let raiz = parentElement.querySelector('.cpf');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'cpf';
      parentElement.appendChild(raiz);
      enlazar(raiz);
      // Al cambiar de ancho, la curva se vuelve a dibujar a su medida.
      let ancho = 0, espera = 0;
      new ResizeObserver(() => {
        if (Math.abs(raiz.clientWidth - ancho) < 2) return;
        ancho = raiz.clientWidth;
        clearTimeout(espera);
        espera = setTimeout(() => { if (G.R && G.F && G.R.sello === G.F.sello) pintarFicha(); }, 120);
      }).observe(raiz);
    }
    G.raices.ficha = raiz;
    if (!G.F || G.F.sello !== data.sello) { G.F = leerFicha(data); G.spark = null; }
  } else {
    let raiz = parentElement.querySelector('.cpr');
    if (!raiz) {
      raiz = document.createElement('div');
      raiz.className = 'cpr';
      raiz.innerHTML = ESQ_RANK;
      parentElement.appendChild(raiz);
      enlazar(raiz);
    }
    G.raices.rank = raiz;
    if (G.rankData !== data) {
      G.rankData = data;
      G.R = leerRank(data);
      G.spark = null;
    }
  }
  pintar();
}
