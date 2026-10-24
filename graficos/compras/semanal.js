// Compras › «Compras por período» (regla #716).
//
// La monta graficos/compras/semanal.py con st.components.v2 (sin iframe,
// estilos en un shadow root). `_xlsx.js` va antepuesto (libro, bajar,
// archivo). Python manda las líneas del rango (de TODOS los documentos, con
// su precio habitual), lo que restaron las notas de crédito y las listas
// del histórico; todo lo demás lo resuelve el navegador: el grano, los
// cuatro filtros, Documento y Montos, «Partir por» y lo resaltado, las
// barras con sus etiquetas, la zona de abajo con sus tres modos y los clics
// en las tablas. Sólo la fecha (un botón de Python, encima de la pieza) pide
// una corrida. El estado vive en `window.__cpPer`: sobrevive a que
// Streamlit vuelva a montar la pieza.
//
// Las cuentas son las de semanal.py (`partes_por_columna`,
// `partes_por_precio`, `_variaciones`, `_rotulo_periodo`, `_plan_etiquetas`,
// `detalle_con_notas`, `_familias_de`, `_resumen_proveedores`): si se toca
// una, se toca la otra. Lo vigila test_compras_periodo.py, que corre
// `calcular` en Chromium contra ellas.

const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
const DIA = 864e5;
// Una línea (semanal.armar_pieza) y una nota de crédito (las doce primeras
// iguales, más la nota y su día).
const RL = { dia: 0, prod: 1, prov: 2, doc: 3, fam: 4, sub: 5, cant: 6, neto: 7, igv: 8, tipo: 9, usd: 10, punit: 11, refT: 12, refS: 13 };
const RN = { nota: 12, diaNc: 13 };
const TIPOS = ['F', 'G', 'O'];
const GRANOS = [['Día', 'Día'], ['Semana', 'Semana'], ['Mes', 'Mes'], ['Año', 'Año'], ['Por documento', 'Documento']];
const MODOS = ['Resumen Total', 'Resumen del Período', 'Detalle'];
const DOCUS = ['Todos', 'Facturas', 'Guías sin canjear'];
const MONTOS = ['Sin IGV', 'Con IGV'];
const SUB = 'Subfamilia', PROV = 'Proveedor', PRECIO = 'Precio';
const A_HABITUAL = 'A precio habitual', DE_MAS = 'Pagado de más', SIN_PREVIO = 'Sin precio previo';
const TITULO_PRECIO = 'Contra el precio habitual · mediana de los 90 días anteriores';
const TOPS = [5, 10, 20];
const PARTES_N = 5, PRODUCTOS_HOVER = 3, HOVER_FAMILIAS = 5, KPI_FAMILIAS = 3, NC_MINIMO = 0.005;
const GRAN_PARTIDA = ['Día', 'Semana', 'Mes', 'Año'];
const GRAN_CON_DOCS = ['Día', 'Semana', 'Mes', 'Año'];
const GRAN_VARIACION = ['Día', 'Semana', 'Mes'];
const TOTAL_DEL = { Día: 'Total del día', Semana: 'Total de la semana', Mes: 'Total del mes', Año: 'Total del año' };
const AGRUPADO = { Día: 'día', Semana: 'semana', Mes: 'mes', Año: 'año', 'Por documento': 'documento' };
const UNIDAD = { Día: ['día', 'días'], Semana: ['semana', 'semanas'], Mes: ['mes', 'meses'], Año: ['año', 'años'],
  'Por documento': ['documento', 'documentos'] };
const INCOMPLETO = { Semana: 'Semana incompleta', Mes: 'Mes incompleto', Año: 'Año incompleto' };
// PALETA_SERIES de tema.py, en las variables de estilos/_00_base.py (la
// octava no tiene variable: va la más cercana, --accent-deep).
const PALETA = ['var(--serie-0)', 'var(--serie-1)', 'var(--serie-2)', 'var(--serie-3)', 'var(--serie-4)',
  'var(--serie-5)', 'var(--serie-6)', 'var(--accent-deep)'];
const C_PRINCIPAL = 'var(--accent)', C_TRAMO0 = 'var(--accent-hover)', C_TRAMO2 = 'var(--border-lavender)';
const C_ERROR = 'var(--danger)', C_GRIS = 'var(--text-muted)';
// Las etiquetas sobre las barras (`_plan_etiquetas`), medidas en DM Sans.
const ETQ_FUENTE = 10, ETQ_PX = 5.4, ETQ_LINEA = 13, ETQ_AIRE = 4;
const TICK_PX = 6.3, TICK_AIRE = 12, PX_DIA_ROTULO = 16, PX_DIA_BANDA = 4, ROTULO_DIA_PX = 44;

// ── Fechas como número de día (UTC) ──────────────────────────────────────
const dn = (s) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d) / DIA; };
const ymd = (n) => { const t = new Date(n * DIA); return [t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()]; };
const p2 = (x) => String(x).padStart(2, '0');
const iso = (n) => { const [y, m, d] = ymd(n); return `${y}-${p2(m)}-${p2(d)}`; };
const diaSemana = (n) => (new Date(n * DIA).getUTCDay() + 6) % 7;
const dmy = (n) => { const [y, m, d] = ymd(n); return `${p2(d)}/${p2(m)}/${y}`; };
const dm = (n) => { const [, m, d] = ymd(n); return `${p2(d)}/${p2(m)}`; };
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
// La semana ISO: de lunes a domingo, con el año de su jueves.
function semanaIso(n) {
  const jue = n - diaSemana(n) + 3, y = ymd(jue)[0];
  return [y, Math.floor((jue - Date.UTC(y, 0, 1) / DIA) / 7) + 1];
}
function lunesIso(y, w) { const e4 = Date.UTC(y, 0, 4) / DIA; return e4 - diaSemana(e4) + (w - 1) * 7; }

// ── Formato ──────────────────────────────────────────────────────────────
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const finito = (v) => v != null && isFinite(v);
// Un formateador por cantidad de decimales: `toLocaleString` arma uno en cada
// llamada, y una tabla de dos mil filas eran 0,8 s sólo de eso.
const FMT = [0, 1, 2, 3, 4].map((d) => new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));
const num = (v, dec) => FMT[dec].format(v);
const s2 = (v) => `${v < 0 ? '−' : ''}S/ ${num(Math.abs(v), 2)}`;
const s2py = (v) => `S/ ${v < 0 ? '-' : ''}${num(Math.abs(v), 2)}`;   // el f"S/ {v:,.2f}" del hover
// utils.fmt_k
function fmtK(v) {
  const m = Math.abs(v);
  if (m >= 1e6) return `S/ ${(v / 1e6).toFixed(1)}M`;
  if (m >= 1e3) return `S/ ${(v / 1e3).toFixed(1)}k`;
  return `S/ ${v.toFixed(0)}`;
}
const pctParte = (p) => { const x = p * 100; return Math.abs(x) < 10 ? `${x.toFixed(1)}%` : `${x.toFixed(0)}%`; };
// _fmt_variacion: «+12%» / «−4.7%» y su color (rojo si se compró más).
function fmtVariacion(pct) {
  const dec = Math.abs(pct) < 10 ? 1 : 0;
  if (Number(Math.abs(pct).toFixed(dec)) === 0) return ['0%', 'cero'];
  const t = `${Math.abs(pct).toFixed(dec)}%`;
  return pct > 0 ? [`+${t}`, 'sube'] : [`−${t}`, 'baja'];
}
const trunc = (s, n = 26) => (String(s).length <= n ? String(s) : String(s).slice(0, n - 1) + '…');
const sinTildes = (s) => String(s).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
const coincide = (nom, q) => sinTildes(q).split(/\s+/).filter(Boolean).every((p) => sinTildes(nom).includes(p));
const suma = (xs, f) => xs.reduce((s, x) => s + f(x), 0);
const pyCmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// ── Los períodos (`_periodo_serie`, `_limites_periodo`, `_rotulo_periodo`) ─
function clave(n, gran) {
  const [y, m] = ymd(n);
  if (gran === 'Día') return iso(n);
  if (gran === 'Semana') { const [a, w] = semanaIso(n); return `${a}-S${p2(w)}`; }
  if (gran === 'Año') return String(y);
  return `${y}-${p2(m)}`;
}
function limites(k, gran) {
  if (gran === 'Semana') { const [a, w] = k.split('-S').map(Number); const l = lunesIso(a, w); return [l, l + 6]; }
  if (gran === 'Mes') { const [a, m] = k.split('-').map(Number); return [Date.UTC(a, m - 1, 1) / DIA, Date.UTC(a, m, 0) / DIA]; }
  if (gran === 'Año') { const a = Number(k); return [Date.UTC(a, 0, 1) / DIA, Date.UTC(a, 11, 31) / DIA]; }
  const x = dn(k); return [x, x];
}
function cobertura(k, gran, rango) {
  const [ini, fin] = limites(k, gran), dias = fin - ini + 1;
  if (!rango) return [dias, dias];
  const a = Math.max(ini, rango[0]), b = Math.min(fin, rango[1]);
  return [Math.max(b - a + 1, 0), dias];
}
// `_variaciones`: por barra, [estado, pct, índice de la anterior].
function variaciones(claves, valores, gran, rango) {
  const parc = claves.map((k) => { const [a, b] = cobertura(k, gran, rango); return a < b; });
  return valores.map((v, i) => {
    const ant = i ? i - 1 : null;
    if (parc[i]) return ['parcial', null, ant];
    if (ant == null) return ['primera', null, null];
    if (parc[ant]) return ['ant_parcial', null, ant];
    if (!valores[ant] || valores[ant] <= 0) return ['sin_base', null, ant];
    return ['ok', (v - valores[ant]) / valores[ant] * 100, ant];
  });
}
// `_hover_variacion` (html) y `_nota_variacion` (texto plano).
function textoVariacion(v, gran, k, nombreAnt, rango, html) {
  if (!v) return '';
  const [estado, pct] = v;
  const it = (t) => (html ? `<br><i>${t}</i>` : t);
  if (estado === 'ok') {
    const [t, c] = fmtVariacion(pct);
    return html ? `<br>vs ${esc(nombreAnt)}: <b class="${c}">${t}</b>` : `vs ${nombreAnt}: ${t}`;
  }
  if (estado === 'parcial') {
    const [n, m] = cobertura(k, gran, rango);
    return it(`${INCOMPLETO[gran] || 'Período incompleto'} en el rango (${n} de ${m} días): sin variación`);
  }
  if (estado === 'ant_parcial') return it(`Sin variación: la barra anterior (${esc(nombreAnt)}) está incompleta en el rango`);
  if (estado === 'sin_base') return it(`Sin variación: ${esc(nombreAnt)} no suma compras`);
  return it('Primera barra del rango: sin anterior para comparar');
}
// `_rotulo_periodo`: [eje, largo].
function rotuloPeriodo(k, gran, rango) {
  if (gran === 'Semana') {
    const [ini, fin] = limites(k, gran);
    const [yi, mi, di] = ymd(ini), [yf, mf, df] = ymd(fin);
    const ai = yi !== yf ? ` ${yi}` : '';
    const semana = mi === mf ? `Semana del lun ${di} al dom ${df} ${MES[mf - 1]} ${yf}`
      : `Semana del lun ${di} ${MES[mi - 1]}${ai} al dom ${df} ${MES[mf - 1]} ${yf}`;
    let a = ini, b = fin;
    if (rango) { a = Math.max(ini, rango[0]); b = Math.min(fin, rango[1]); if (a > b) { a = ini; b = fin; } }
    const dia = (x, conMes) => { const [, m, d] = ymd(x); return `${DIAS[diaSemana(x)]} ${d}` + (conMes ? ` ${MES[m - 1]}` : ''); };
    const mesA = ymd(a)[1], mesB = ymd(b)[1];
    let eje;
    if (a === b) eje = dia(a, true);
    else if (mesA === mesB) eje = `${dia(a, false)}–${dia(b, true)}`;
    else eje = `${dia(a, true)}–${dia(b, true)}`;
    if (a === ini && b === fin) return [eje, semana];
    const dias = a === b ? `${dia(a, true)} ${ymd(a)[0]}` : `Del ${dia(a, mesA !== mesB)} al ${dia(b, true)} ${ymd(b)[0]}`;
    return [eje, `${cap(dias)} · la ${semana.charAt(0).toLowerCase()}${semana.slice(1)} queda cortada por las fechas`];
  }
  if (gran === 'Mes') { const [ini] = limites(k, gran); const [y, m] = ymd(ini); const t = `${MES[m - 1]} ${y}`; return [t, cap(t)]; }
  return [k, k];
}
function anioSemana(k) { const [ini, fin] = limites(k, 'Semana'); const a = ymd(ini)[0], b = ymd(fin)[0]; return a === b ? String(b) : `${a}-${p2(b % 100)}`; }
// `_del_al`: los días CON compras de las barras.
function delAl(dias) {
  if (!dias.length) return 'Todo el rango';
  const ini = Math.min(...dias), fin = Math.max(...dias), [ya, ma, da] = ymd(ini), [yb, mb, db] = ymd(fin);
  if (ini === fin) return `El ${da} ${MES[ma - 1]} ${ya}`;
  if (ya === yb) return `Del ${da} ${MES[ma - 1]} al ${db} ${MES[mb - 1]} ${yb}`;
  return `Del ${da} ${MES[ma - 1]} ${ya} al ${db} ${MES[mb - 1]} ${yb}`;
}

// ── Los datos ────────────────────────────────────────────────────────────
function leer(data) {
  const base = dn(data.base);
  const fila = (r, i) => ({ i, d: base + r[RL.dia], prod: r[RL.prod], prov: r[RL.prov], doc: r[RL.doc], fam: r[RL.fam], sub: r[RL.sub],
    cant: r[RL.cant] || 0, neto: r[RL.neto] || 0, igv: r[RL.igv] || 0, tipo: TIPOS[r[RL.tipo]] || 'O', usd: !!r[RL.usd],
    punit: r[RL.punit] });
  const L = data.lineas.map((r, i) => ({ ...fila(r, i), refT: r[RL.refT], refS: r[RL.refS] }));
  const N = (data.notas || []).map((r, i) => ({ ...fila(r, i), nota: r[RN.nota], dNc: base + r[RN.diaNc] }));
  const feriados = new Set((data.feriados || []).map(dn));
  const famSubs = new Map(Object.entries(data.fam_subs || {}).map(([k, v]) => [Number(k), v]));
  return { sello: data.sello, R0: dn(data.rango[0]), R1: dn(data.rango[1]), feriados, L, N,
    provs: data.provs, provN: data.prov_n, provC: data.prov_c, prods: data.prods, docs: data.docs,
    fams: data.fams, famN: data.fam_n, subs: data.subs, subN: data.sub_n, famOps: data.fam_ops, subOps: data.sub_ops, famSubs,
    ordSub: data.ord_sub, nOrdSub: data.n_ord_sub, ordProv: data.ord_prov, nOrdProv: data.n_ord_prov,
    notaTxt: data.nota_txt || [], notaDoc: data.nota_doc || [], techo: data.etq_techo || 0.45,
    hayFam: !!data.hay_fam, haySub: !!data.hay_sub, hayProv: !!data.hay_prov, hayCant: !!data.hay_cant,
    hayDoc: !!data.hay_doc, hayTipo: !!data.hay_tipo, hayIgv: !!data.hay_igv };
}

// `colores_estables`: el color por el puesto en el histórico; si dos de las
// que se dibujan juntas caen en el mismo, la segunda toma el siguiente libre.
function coloresEstables(ord, nOrd, nombres) {
  const usados = new Set(), salida = new Map();
  nombres.forEach((a) => {
    let i = ord[a] != null ? ord[a] : nOrd + salida.size;
    let c = PALETA[i % PALETA.length];
    while (usados.has(c) && usados.size < PALETA.length) { i += 1; c = PALETA[i % PALETA.length]; }
    usados.add(c); salida.set(a, c);
  });
  return salida;
}
// `partes_por_columna`: las `PARTES_N` mayores de la vista y el resto en gris.
function partesColumna(dd, campo, claves, ord, nOrd, resto, nombrar) {
  const tot = new Map();
  dd.forEach((l) => tot.set(l[campo], (tot.get(l[campo]) || 0) + l.v));
  const pos = [...tot.entries()].filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  if (!pos.length) return [];
  const nombres = pos.length <= PARTES_N + 1 ? pos.map((x) => x[0]) : pos.slice(0, PARTES_N).map((x) => x[0]);
  const color = coloresEstables(ord, nOrd, nombres);
  const ix = new Map(claves.map((k, j) => [k, j]));
  const por = new Map(nombres.map((c) => [c, claves.map(() => 0)]));
  const totales = claves.map(() => 0);
  dd.forEach((l) => { const j = ix.get(l.clave); if (j == null) return; totales[j] += l.v; const a = por.get(l[campo]); if (a) a[j] += l.v; });
  const partes = nombres.map((c) => [nombrar(c), color.get(c), por.get(c)]);
  if (nombres.length < pos.length) {
    const acum = claves.map((k, j) => suma(nombres, (c) => por.get(c)[j]));
    partes.push([`${resto} (${pos.length - nombres.length})`, C_GRIS, totales.map((t, j) => Math.max(t - acum[j], 0))]);
  }
  return partes;
}
// `partes_por_precio`: lo pagado al habitual, de más, y sin precio previo.
function partesPrecio(dd, claves, F) {
  const ix = new Map(claves.map((k, j) => [k, j]));
  const z = () => claves.map(() => 0);
  const g = { sin: z(), hp: z(), mas: z(), menos: z(), hab: z(), pag: z() };
  const prods = new Map();
  dd.forEach((l) => {
    const j = ix.get(l.clave);
    if (j == null) return;
    const con = finito(l.ref) && l.cant > 0 && l.v > 0;
    if (!con) { g.sin[j] += l.v; return; }
    const hab = l.cant * l.ref, mas = Math.max(l.v - hab, 0);
    g.hp[j] += l.v - mas; g.mas[j] += mas; g.menos[j] += Math.max(hab - l.v, 0); g.hab[j] += hab; g.pag[j] += l.v;
    if (mas > 0) {
      const k = `${l.clave}\u0001${l.prod}`;
      const a = prods.get(k) || { clave: l.clave, prod: l.prod, mas: 0, hab: 0 };
      a.mas += mas; a.hab += hab; prods.set(k, a);
    }
  });
  const todas = [[A_HABITUAL, C_PRINCIPAL, g.hp, 1], [DE_MAS, C_ERROR, g.mas, 2], [SIN_PREVIO, C_GRIS, g.sin, 0]];
  const vivas = todas.filter((p) => suma(p[2], (x) => Math.abs(x)) > 0);
  const partes = vivas.map(([r, c, v]) => [r, c, v]);
  const pila = vivas.map((p, i) => i).sort((a, b) => vivas[a][3] - vivas[b][3]);
  const porClave = new Map();
  [...prods.values()].sort((a, b) => pyCmp(a.clave, b.clave) || b.mas - a.mas || pyCmp(F.prods[a.prod], F.prods[b.prod]))
    .forEach((a) => {
      const xs = porClave.get(a.clave) || [];
      if (xs.length < PRODUCTOS_HOVER) xs.push(`${esc(trunc(F.prods[a.prod], 30))}: +S/ ${num(a.mas, 2)} (+${pctParte(a.hab ? a.mas / a.hab : 0)})`);
      porClave.set(a.clave, xs);
    });
  const extra = claves.map((k, j) => {
    const r = [];
    if (g.menos[j]) r.push(`Pagado de menos: S/ ${num(g.menos[j], 2)}`);
    if (g.hab[j]) {
      const neto = g.pag[j] - g.hab[j], [t, c] = fmtVariacion(neto / g.hab[j] * 100);
      const sg = neto > 0 ? '+' : neto < 0 ? '−' : '';
      r.push(`Neto: <b class="${c}">${sg}S/ ${num(Math.abs(neto), 2)} (${t})</b> contra el precio habitual`);
    }
    if (porClave.has(k)) r.push(`<span class="gr">Lo que más se pagó de más</span><br>${porClave.get(k).join('<br>')}`);
    return r.map((x) => `<br>${x}`).join('');
  });
  return { partes, pila, extra };
}
// `_familias_de`: el total, las `n` mayores y el resto sumado.
function familiasDe(dd, n) {
  const s = new Map();
  dd.forEach((l) => s.set(l.fam, (s.get(l.fam) || 0) + l.v));
  const xs = [...s.entries()].filter(([, v]) => v !== 0).sort((a, b) => b[1] - a[1]);
  if (xs.length === n + 1) n += 1;
  return { top: xs.slice(0, n), resto: [xs.length - Math.min(n, xs.length), suma(xs.slice(n), (x) => x[1])] };
}
// `detalle_con_notas`: la factura como se facturó y la nota como un
// documento más, en negativo y en su fecha.
function detalleConNotas(dd, ncd, lblDe) {
  if (!ncd.length) return dd;
  const tocadas = new Set(ncd.map((n) => n.compra));
  const fact = new Map();
  [...dd.filter((l) => tocadas.has(l.compra)), ...ncd].forEach((l) => {
    const k = `${l.compra}\u0001${l.prod}`;
    const a = fact.get(k);
    if (!a) fact.set(k, { ...l, lbl: l.lbl ?? lblDe.get(l.clave), nc: false });
    else { a.cant += l.cant; a.v += l.v; a.neto += l.neto; a.igv += l.igv; }
  });
  const notas = ncd.map((n) => ({ ...n, cant: -n.cant, v: -n.v, neto: -n.neto, igv: -n.igv, d: n.dNc, tipo: 'N', usd: false,
    docLeg: n.notaDoc, compra: `NC·${n.notaPri}·${n.provRaw}`, lbl: lblDe.get(n.clave), nc: true }));
  return [...dd.filter((l) => !tocadas.has(l.compra)), ...fact.values(), ...notas];
}

// Todo lo que la pieza dibuja con un estado dado. Pura (salvo que corrige
// las selecciones que dejaron de ofrecerse, como `seleccion_multiple`).
function calcular(F, st) {
  const V = {};
  const docu = F.hayTipo ? st.docu : 'Todos';
  const okTipo = (t) => docu === 'Todos' || (docu === 'Facturas' ? t === 'F' : t === 'G');
  const conIgv = st.montos === 'Con IGV' && F.hayIgv;
  const L = F.L.filter((l) => okTipo(l.tipo));
  L.forEach((l) => { l.v = l.neto + (conIgv ? l.igv : 0); });
  // Las opciones, de izquierda a derecha (regla #623): Familia y Subfamilia
  // del histórico; Proveedor y Producto del rango, por valor.
  const famOps = F.hayFam ? F.famOps.map((i) => F.fams[i]) : [];
  st.fam = st.fam.filter((x) => famOps.includes(x));
  let subOps = [];
  if (F.haySub) {
    if (st.fam.length) {
      const set = new Set();
      st.fam.forEach((f) => (F.famSubs.get(F.fams.indexOf(f)) || []).forEach((s) => set.add(s)));
      subOps = [...set].map((i) => F.subs[i]).sort();
    } else subOps = F.subOps.map((i) => F.subs[i]);
  }
  st.sub = st.sub.filter((x) => subOps.includes(x));
  const famSel = new Set(st.fam), subSel = new Set(st.sub);
  const L1 = L.filter((l) => (!famSel.size || famSel.has(F.fams[l.fam])) && (!subSel.size || subSel.has(F.subs[l.sub])));
  const porValor = (ls, campo, nombres) => {
    const m = new Map();
    ls.forEach((l) => m.set(l[campo], (m.get(l[campo]) || 0) + l.v));
    return [...m.entries()].sort((a, b) => b[1] - a[1] || pyCmp(nombres[a[0]], nombres[b[0]])).map((x) => nombres[x[0]]);
  };
  let provOps = F.hayProv ? porValor(L1, 'prov', F.provs) : [];
  const conservar = (sel, ops, soltar) => {
    const en = new Set(ops), fuera = new Set(soltar || []);
    const vig = sel.filter((x) => en.has(x) || !fuera.has(x));
    return [vig, [...ops, ...vig.filter((x) => !en.has(x))]];
  };
  [st.prov, provOps] = conservar(st.prov, provOps);
  const provSel = new Set(st.prov);
  const L2 = provSel.size ? L1.filter((l) => provSel.has(F.provs[l.prov])) : L1;
  const prods = porValor(L2, 'prod', F.prods);
  const etiqTop = new Map(TOPS.map((n) => [`Top ${n} por valor`, n]));
  let prodOps = [...[...etiqTop.entries()].filter(([, n]) => n < prods.length).map(([e]) => e), ...prods];
  [st.prod, prodOps] = conservar(st.prod, prodOps, [...etiqTop.keys()]);
  const nTop = Math.max(0, ...st.prod.filter((p) => etiqTop.has(p)).map((p) => etiqTop.get(p)));
  const prodsSel = new Set([...prods.slice(0, nTop), ...st.prod.filter((p) => !etiqTop.has(p))]);
  Object.assign(V, { famOps, subOps, provOps, prodOps, docu, conIgv });
  const filtrar = (ls) => ls.filter((l) => (!famSel.size || famSel.has(F.fams[l.fam])) && (!subSel.size || subSel.has(F.subs[l.sub]))
    && (!provSel.size || provSel.has(F.provs[l.prov])) && (!st.prod.length || prodsSel.has(F.prods[l.prod])));
  let dd = filtrar(L);
  // «Partir por» y si Precio fuerza el neto (regla #621).
  const opsPartir = [[SUB, F.haySub], [PROV, F.hayProv], [PRECIO, F.hayCant]].filter((x) => x[1]).map((x) => x[0]);
  if (opsPartir.length && !opsPartir.includes(st.partir)) st.partir = opsPartir.includes(SUB) ? SUB : opsPartir[0];
  const gran = st.gran;
  const partidaGran = GRAN_PARTIDA.includes(gran) && opsPartir.length > 0;
  const forzarNeto = conIgv && partidaGran && st.partir === PRECIO;
  if (forzarNeto) dd = dd.map((l) => ({ ...l, v: l.neto }));
  else dd = dd.map((l) => ({ ...l }));
  const igvVista = conIgv && !forzarNeto;
  let sufijo = igvVista ? ' · con IGV' : ' · sin IGV';
  if (docu === 'Facturas') sufijo += ' · facturas'; else if (docu === 'Guías sin canjear') sufijo += ' · guías sin canjear';
  if (forzarNeto) sufijo += ' (Precio se compara sin IGV)';
  const ambDe = (sel, plural, fmt = (x) => x) => (!sel.length ? null : sel.length === 1 ? fmt(sel[0]) : `${sel.length} ${plural}`);
  const amb = [ambDe(st.fam, 'familias'), ambDe(st.sub, 'subfamilias'),
    ambDe(st.prov, 'proveedores', (p) => trunc(F.provN[F.provs.indexOf(p)] || p)),
    st.prod.length < 2 ? ambDe(st.prod, 'productos') : `${prodsSel.size} productos`].filter(Boolean);
  const titGran = { Día: 'por día', Semana: 'por semana', Mes: 'por mes', Año: 'por año', 'Por documento': 'por documento' }[gran];
  Object.assign(V, { opsPartir, partidaGran, forzarNeto, igvVista, sufijo, rotValor: igvVista ? 'con IGV' : 'sin IGV',
    titulo: `Compra ${titGran}` + (amb.length ? ' · ' + amb.join(' · ') : ''), gran });
  if (!dd.length) { V.vacio = true; return V; }

  // La clave de COMPRA (fecha·proveedor·documento) y la del período.
  const pad6 = (x) => String(x).padStart(6, '0');
  const compraDe = (l) => (F.hayDoc ? `${iso(l.d)}·${F.provs[l.prov]}·${pad6(l.doc)}` : String(l.i));
  dd.forEach((l) => { l.compra = compraDe(l); l.clave = gran === 'Por documento' ? l.compra : clave(l.d, gran); l.docLeg = F.docs[l.doc]; });
  const rango = [F.R0, F.R1];
  const claves = [...new Set(dd.map((l) => l.clave))].sort(pyCmp);
  const n = claves.length, ix = new Map(claves.map((k, j) => [k, j]));
  const rotDe = new Map();
  if (gran !== 'Por documento') claves.forEach((k) => rotDe.set(k, rotuloPeriodo(k, gran, rango)));
  const diaDe = claves.map(() => Infinity), tot = claves.map(() => 0), cant = claves.map(() => 0);
  const compras = claves.map(() => new Set()), nlin = claves.map(() => 0), primera = claves.map(() => null);
  dd.forEach((l) => {
    const j = ix.get(l.clave);
    diaDe[j] = Math.min(diaDe[j], l.d); tot[j] += l.v; cant[j] += l.cant; compras[j].add(l.compra); nlin[j] += 1;
    if (!primera[j]) primera[j] = l;
  });
  const lbls = claves.map((k, j) => (gran === 'Por documento' ? dm(primera[j].d) : rotDe.get(k)[0]));
  const lblDe = new Map(claves.map((k, j) => [k, lbls[j]]));
  dd.forEach((l) => { l.lbl = lblDe.get(l.clave); });
  // El encabezado del hover.
  const hov = claves.map((k, j) => {
    if (gran === 'Por documento' || gran === 'Día') {
      const x = diaDe[j];
      let h = `${cap(DIAS[diaSemana(x)])} ${dmy(x)}` + (F.feriados.has(x) ? ' · feriado' : '');
      if (gran === 'Por documento') h += `<br>${esc(primera[j].docLeg)} · ${esc(trunc(F.provN[primera[j].prov] || ''))}`;
      return h;
    }
    return esc(rotDe.get(k)[1]);
  });
  // El desglose por familia, sólo en «Por documento» (`_familias_por_clave`).
  let famHov = claves.map(() => '');
  if (gran === 'Por documento' && new Set(dd.map((l) => l.fam)).size > 1) {
    const m = new Map();
    dd.forEach((l) => { const k = `${l.clave}\u0001${l.fam}`; m.set(k, (m.get(k) || 0) + l.v); });
    const por = new Map();
    m.forEach((v, k) => { if (v === 0) return; const [c, f] = k.split('\u0001'); (por.get(c) || por.set(c, []).get(c)).push([Number(f), v]); });
    famHov = claves.map((k) => {
      const xs = (por.get(k) || []).sort((a, b) => b[1] - a[1]);
      if (!xs.length) return '';
      const t = suma(xs, (x) => x[1]);
      let h = xs.slice(0, HOVER_FAMILIAS).map(([f, v]) => `${esc(F.famN[f])}: S/ ${num(v, 2)} · ${Math.round(t ? v / t * 100 : 0)}%`).join('<br>');
      if (xs.length > HOVER_FAMILIAS) h += `<br>${xs.length - HOVER_FAMILIAS} más: S/ ${num(suma(xs.slice(HOVER_FAMILIAS), (x) => x[1]), 2)}`;
      return `<br><span class="gr">Por familia</span><br>${h}`;
    });
  }
  // Las notas de crédito de la vista (regla #628), medidas como la barra.
  let ncd = filtrar(F.N.filter((l) => okTipo(l.tipo))).map((l) => ({ ...l, v: l.neto + (igvVista ? l.igv : 0) }));
  ncd.forEach((l) => {
    l.compra = compraDe(l); l.clave = gran === 'Por documento' ? l.compra : clave(l.d, gran); l.docLeg = F.docs[l.doc];
    l.provRaw = F.provs[l.prov]; l.notaPri = (F.notaTxt[l.nota] || '').split(', ')[0]; l.notaDoc = F.notaDoc[l.nota] || l.notaPri;
  });
  const ncTot = suma(ncd, (l) => l.v);
  const ncDe = new Map();
  ncd.forEach((l) => ncDe.set(l.clave, (ncDe.get(l.clave) || 0) + l.v));
  const ddDet = detalleConNotas(dd, ncd, lblDe);
  Object.assign(V, { dd, ddDet, ncd, ncTot, ncDe, claves, n, ix, lbls, lblDe, rotDe, diaDe, tot, cant, nlin, hov, famHov, primera,
    ndocs: compras.map((s) => s.size), rango });

  // El modo y el foco (los valida contra lo que hay).
  const focoOk = claves.includes(st.foco);
  const docOk = st.doc != null && ddDet.some((l) => l.compra === st.doc);
  const provOk = st.provDet != null && dd.some((l) => F.provs[l.prov] === st.provDet);
  const conDetalle = focoOk || docOk || provOk;
  Object.assign(V, { focoOk, docOk, provOk, conDetalle, conTabla: conDetalle || st.modo !== 'Detalle' });

  // «Partir por» (reglas #620 y #621).
  let partes = [], pila = [], extra = claves.map(() => ''), titPartes = '';
  if (partidaGran && st.partir === SUB) {
    partes = partesColumna(dd, 'sub', claves, F.ordSub, F.nOrdSub, 'Otras', (s) => F.subN[s]);
    titPartes = 'Por subfamilia';
  } else if (partidaGran && st.partir === PROV) {
    partes = partesColumna(dd, 'prov', claves, F.ordProv, F.nOrdProv, 'Otros', (p) => F.provC[p]);
    titPartes = 'Por proveedor';
  } else if (partidaGran && st.partir === PRECIO) {
    dd.forEach((l) => { l.ref = docu === 'Todos' ? l.refT : l.refS; });
    ({ partes, pila, extra } = partesPrecio(dd, claves, F));
    titPartes = TITULO_PRECIO;
  }
  const partida = partes.length > 0;
  const esResto = (r) => /^(Otras|Otros) \(/.test(r);
  const opsRes = !partida ? [] : st.partir === PRECIO ? partes.filter((p) => p[0] === DE_MAS).map((p) => p[0])
    : partes.filter((p) => !esResto(p[0])).map((p) => p[0]);
  if (opsRes.length && (!(st.partir in st.res) || (st.res[st.partir] != null && !opsRes.includes(st.res[st.partir])))) {
    st.res[st.partir] = opsRes[0];
  }
  const resaltado = opsRes.length ? st.res[st.partir] : null;
  const kRes = partes.findIndex((p) => p[0] === resaltado);
  Object.assign(V, { partes, pila, extra, titPartes, partida, opsRes, resaltado, kRes: kRes < 0 ? null : kRes });

  // La etiqueta de cada barra (#440, #454, #470): sus renglones.
  const vars = GRAN_VARIACION.includes(gran) ? variaciones(claves, tot, gran, rango) : claves.map(() => null);
  const nombreCorto = claves.map((k, j) => (gran === 'Día' ? `${cap(DIAS[diaSemana(diaDe[j])])} ${dm(diaDe[j])}` : lbls[j]));
  V.vars = vars;
  V.varHov = claves.map((k, j) => textoVariacion(vars[j], gran, k, vars[j] && vars[j][2] != null ? nombreCorto[vars[j][2]] : '', rango, true));
  V.varNota = claves.map((k, j) => textoVariacion(vars[j], gran, k, vars[j] && vars[j][2] != null ? nombreCorto[vars[j][2]] : '', rango, false));
  V.reng = claves.map((k, j) => {
    if (!tot[j]) return [];
    const t = fmtK(tot[j]), r = [[t, esc(t)]];
    if (GRAN_CON_DOCS.includes(gran)) { const d = `${num(V.ndocs[j], 0)} doc${V.ndocs[j] === 1 ? '' : 's'}`; r.push([d, `<tspan class="gr">${d}</tspan>`]); }
    const v = vars[j];
    if (GRAN_VARIACION.includes(gran) && v) {
      if (v[0] === 'ok') { const [tx, c] = fmtVariacion(v[1]); r.push([tx, `<tspan class="${c} b">${tx}</tspan>`]); } else if (v[0] === 'parcial') r.push(['parcial', '<tspan class="gr it">parcial</tspan>']);
    }
    // Con una parte resaltada, el renglón de los documentos dice cuánto vale.
    if (V.kRes != null && r.length > 1) {
      const val = partes[V.kRes][2][j];
      if (st.partir === PRECIO) {
        if (val) { const tx = `+${fmtK(val)} de más`; r[1] = [tx, `<tspan class="sube b">${tx}</tspan>`]; }
      } else { const tx = `${val ? fmtK(val) : 'S/ 0'} · ${pctParte(tot[j] ? val / tot[j] : 0)}`; r[1] = [tx, `<tspan class="tramo b">${tx}</tspan>`]; }
    }
    return r;
  });
  return V;
}

// `_plan_etiquetas`: [forma, k, alto] con los píxeles reales del slot y del área.
function planEtiquetas(reng, pxSlot, altoArea, techo) {
  const lineas = reng.filter((r) => r.length).map((r) => r.map((x) => x[0]));
  if (!lineas.length) return [null, 0, 0];
  const altoMax = altoArea * techo, px = (nc) => nc * ETQ_PX + ETQ_AIRE;
  for (let k = Math.max(...lineas.map((l) => l.length)); k > 0; k -= 1) {
    const cortas = lineas.map((l) => l.slice(0, k));
    const nLin = Math.max(...cortas.map((l) => l.length));
    const largo = Math.max(...cortas.flatMap((l) => l.map((t) => t.length)));
    const unida = Math.max(...cortas.map((l) => l.join(' · ').length));
    const altoLin = nLin * ETQ_LINEA + ETQ_AIRE;
    if (px(largo) <= pxSlot && altoLin <= altoMax) return ['derecha', k, altoLin];
    if (altoLin <= pxSlot && px(largo) <= altoMax) return ['girada', k, px(largo)];
    if (nLin > 1 && ETQ_LINEA + ETQ_AIRE <= pxSlot && px(unida) <= altoMax) return ['unida', k, px(unida)];
  }
  return [null, 0, 0];
}

window.__cpPerCalc = { leer, calcular, rotuloPeriodo, variaciones, partesColumna, partesPrecio, familiasDe,
  detalleConNotas, planEtiquetas, clave, semanaIso, coloresEstables };

const G = window.__cpPer || (window.__cpPer = { st: null, F: null, raiz: null });
G.tandas = G.tandas || {};
const estadoInicial = () => ({ gran: 'Semana', fam: [], sub: [], prov: [], prod: [], docu: 'Todos', montos: 'Sin IGV',
  partir: SUB, res: {}, modo: 'Resumen Total', foco: null, doc: null, provDet: null, menu: null, q: {}, orden: {}, ctx: '' });

// ── El gráfico ───────────────────────────────────────────────────────────
function grafico(F, V, st, W, H) {
  const n = V.n, gran = V.gran;
  const diario = gran === 'Día' || gran === 'Por documento';
  // Los días del eje y sus tramos contiguos (`_grupos_de_dia`).
  const grupos = [];
  if (diario) V.diaDe.forEach((d, i) => { const g = grupos[grupos.length - 1]; if (g && g[2] === d) g[1] = i; else grupos.push([i, i, d]); });
  const PL = 46, PR = 10, PB = 32;
  const plotW0 = Math.max(60, W - PL - PR);
  const pxDia = diario ? plotW0 / Math.max(grupos.length, 1) : 0;
  const ferIx = diario && pxDia >= PX_DIA_BANDA ? grupos.map((g, j) => (F.feriados.has(g[2]) ? j : -1)).filter((j) => j >= 0) : [];
  const PT = ferIx.length ? 18 : 8;
  const plotW = plotW0, plotH = Math.max(40, H - PT - PB);
  const slot = plotW / n, bw = Math.max(1, slot * 0.8);
  const X = (i) => PL + (i + 0.5) * slot;
  const tot = V.tot;
  const [forma, k, altoEtq] = planEtiquetas(V.reng, slot, plotH, F.techo);
  const hi = Math.max(0, ...tot), lo = Math.min(0, ...tot);
  let y0 = lo, y1 = hi || 1;
  if (forma) { const a = Math.min(altoEtq, plotH * F.techo); y1 = lo + (hi - lo) * plotH / (plotH - a); } else y1 = hi * 1.06 || 1;
  const Y = (v) => PT + plotH - (v - y0) / (y1 - y0) * plotH;
  const redondo = (r) => { const b = Math.pow(10, Math.floor(Math.log10(r || 1))); const f = r / b; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * b; };
  const fmtY = (v) => (Math.abs(v) >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `${+(v / 1e3).toFixed(1)}k` : String(+v.toFixed(1)));
  let svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(V.titulo)}">`;
  // El calendario (`_calendario_del_eje`): bandas de fin de semana y feriado.
  if (diario && pxDia >= PX_DIA_BANDA) {
    grupos.forEach(([i0, i1, d]) => {
      const fer = F.feriados.has(d), finde = diaSemana(d) >= 5;
      if (fer || finde) svg += `<rect class="${fer ? 'b-fer' : 'b-finde'}" x="${(PL + i0 * slot).toFixed(1)}" y="${PT}" width="${((i1 - i0 + 1) * slot).toFixed(1)}" height="${plotH}"/>`;
    });
    const rachas = [];
    ferIx.forEach((j) => { const r = rachas[rachas.length - 1]; if (r && r[1] === j - 1) r[1] = j; else rachas.push([j, j]); });
    rachas.forEach(([a, b]) => { svg += `<text class="t-fer" x="${((X(grupos[a][0]) + X(grupos[b][1])) / 2).toFixed(1)}" y="${PT - 5}" text-anchor="middle">feriado</text>`; });
  }
  const paso = redondo((y1 - y0) / 4);
  for (let v = Math.ceil(y0 / paso) * paso; v <= y1 * 1.0001; v += paso) {
    svg += `<line class="gl" x1="${PL}" x2="${W - PR}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/>`
      + `<text class="ty" x="${PL - 6}" y="${(Y(v) + 3.5).toFixed(1)}" text-anchor="end">${fmtY(v)}</text>`;
  }
  // Las barras: lisas o con UNA parte resaltada, apoyada en la base (#621).
  let capas;
  if (!V.partida || V.kRes == null) capas = [[tot, tot.map(() => 0), 'lisa']];
  else if (st.partir === PRECIO) { const mas = V.partes[V.kRes][2]; const resto = tot.map((t, j) => t - mas[j]); capas = [[resto, tot.map(() => 0), 'lisa'], [mas, resto, 'mas']]; } else { const p = V.partes[V.kRes][2]; capas = [[p, tot.map(() => 0), 'res'], [tot.map((t, j) => t - p[j]), p, 'resto']]; }
  const marcar = V.conDetalle && st.modo === 'Detalle' && !V.provOk;
  capas.forEach(([ys, bases, cls]) => {
    ys.forEach((y, i) => {
      if (!y) return;
      const a = Y(bases[i]), b = Y(bases[i] + y), top = Math.min(a, b), h = Math.max(0.5, Math.abs(a - b));
      const dim = marcar && V.claves[i] !== st.foco ? ' dim' : '';
      svg += `<rect class="bar ${cls}${dim}" x="${(X(i) - bw / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}"/>`;
    });
  });
  // Las etiquetas.
  if (forma) {
    V.reng.forEach((r, i) => {
      if (!r.length) return;
      const ls = r.slice(0, k), yTop = Y(Math.max(tot[i], 0)) - 3, x = X(i);
      if (forma === 'derecha') {
        svg += `<text class="etq" x="${x.toFixed(1)}" text-anchor="middle">` + ls.map((l, j) => `<tspan x="${x.toFixed(1)}" y="${(yTop - (ls.length - 1 - j) * ETQ_LINEA).toFixed(1)}">${l[1]}</tspan>`).join('') + '</text>';
      } else if (forma === 'girada') {
        svg += ls.map((l, j) => `<text class="etq" transform="translate(${(x + (j - (ls.length - 1) / 2) * ETQ_LINEA + 3.5).toFixed(1)},${yTop.toFixed(1)}) rotate(-90)">${l[1]}</text>`).join('');
      } else {
        svg += `<text class="etq" transform="translate(${(x + 3.5).toFixed(1)},${yTop.toFixed(1)}) rotate(-90)">${ls.map((l) => l[1]).join('<tspan class="gr"> · </tspan>')}</text>`;
      }
    });
  }
  // El eje: un rótulo por día (con las punteadas) o el de cada período.
  let ticks = null;
  if (diario && pxDia >= PX_DIA_ROTULO) {
    grupos.forEach(([i0, , d], j) => {
      if (!j || (gran === 'Día' && diaSemana(d) !== 0)) return;
      const x = PL + i0 * slot;
      svg += `<line class="sep" x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${PT}" y2="${PT + plotH}"/>`;
    });
    const cada = Math.max(1, Math.ceil(grupos.length / Math.max(1, Math.floor(plotW / ROTULO_DIA_PX))));
    // En «Documento» un día con pocas compras es angosto: además del paso
    // parejo, el rótulo que caería encima del anterior se saltea.
    let ultX = -Infinity;
    ticks = grupos.filter((g, j) => !(j % cada)).map(([i0, i1, d]) => [(X(i0) + X(i1)) / 2, cap(DIAS[diaSemana(d)]), dm(d)])
      .filter(([x]) => { if (x - ultX < ROTULO_DIA_PX) return false; ultX = x; return true; });
  }
  if (!ticks) {
    // En «Día» con muchos días el rótulo es «24 jul» y no la clave ISO.
    const rot = gran === 'Día' ? V.diaDe.map((d) => { const [, m, dd] = ymd(d); return `${dd} ${MES[m - 1]}`; }) : V.lbls;
    const largo = Math.max(1, ...rot.map((l) => l.length));
    const caben = Math.max(1, Math.floor(plotW / (largo * TICK_PX + TICK_AIRE)));
    const cada = Math.max(1, Math.ceil(n / caben));
    let ult = null;
    ticks = [];
    for (let i = 0; i < n; i += cada) {
      let sub = '';
      if (gran === 'Semana') { const a = anioSemana(V.claves[i]); if (a !== ult) { sub = a; ult = a; } }
      ticks.push([X(i), rot[i], sub]);
    }
  }
  ticks.forEach(([x, a, b]) => {
    svg += `<text class="tx" x="${x.toFixed(1)}" y="${PT + plotH + 14}" text-anchor="middle">${esc(a)}</text>`;
    if (b) svg += `<text class="tx sub" x="${x.toFixed(1)}" y="${PT + plotH + 26}" text-anchor="middle">${esc(b)}</text>`;
  });
  for (let i = 0; i < n; i += 1) svg += `<rect class="hit" data-acc="barra" data-v="${i}" x="${(PL + i * slot).toFixed(1)}" y="${PT}" width="${slot.toFixed(1)}" height="${plotH}"></rect>`;
  return { svg: svg + '</svg>', X };
}

// El hover de una barra (el `hovertemplate` de antes).
function tip(F, V, st, i) {
  const t = V.tot[i];
  const docs = ` · ${num(V.ndocs[i], 0)} doc${V.ndocs[i] === 1 ? '' : 's'}`;
  let h = `<b>${V.hov[i]}</b>`;
  if (!V.partida) {
    h += `<br>Valor: S/ ${num(t, 2)}<br>Cantidad: ${num(V.cant[i], 1)}${V.famHov[i]}`;
    return h;
  }
  h += `<br>${TOTAL_DEL[V.gran] || 'Total del período'} ${V.rotValor}: ${s2py(t)}${docs}`;
  if (V.igvVista) {
    let ne = 0, ig = 0;
    V.dd.forEach((l) => { if (l.clave === V.claves[i]) { ne += l.neto; ig += l.igv; } });
    h += `<br><span class="gr">neto S/ ${num(ne, 2)} + IGV S/ ${num(ig, 2)}</span>`;
  }
  h += V.varHov[i];
  h += `<br><span class="gr">${esc(V.titPartes)}</span>`;
  V.partes.forEach(([r, , vals], k) => {
    if (!vals[i]) return;
    const x = `${esc(r)}: S/ ${num(vals[i], 2)} · ${pctParte(t ? vals[i] / t : 0)}`;
    h += k === V.kRes ? `<br><b>${x}</b>` : `<br>${x}`;
  });
  h += V.extra[i] || '';
  // Cuánto de la barra es guía sin canjear (regla #621).
  const gs = V.dd.filter((l) => l.clave === V.claves[i] && l.tipo === 'G');
  if (gs.length) {
    const nota = V.igvVista ? ' · sin IGV todavía: lo trae la factura' : '';
    const nG = new Set(gs.map((l) => l.compra)).size;
    h += `<br><span class="aviso">${V.docu === 'Guías sin canjear' ? 'Guías de remisión sin canjear' + nota
      : `Incluye ${nG} guía${nG === 1 ? '' : 's'} de remisión sin canjear: S/ ${num(suma(gs, (l) => l.v), 2)}${nota}`}</span>`;
  }
  return h;
}

// ── La zona de abajo: tres tablas ───────────────────────────────────────
// Una tabla ordenable: `cols` = [clave, rótulo, clase, formato, ayuda]; la
// fila TOTAL se escribe ya formateada.
const TANDA = 150;
function tabla(id, cols, filas, total, st, opts = {}) {
  const o = st.orden[id] || opts.orden || null;
  if (o) {
    const c = cols.find((x) => x[0] === o.col);
    if (c) filas = filas.slice().sort((a, b) => { const x = a.s[o.col] ?? a.v[o.col], y = b.s[o.col] ?? b.v[o.col]; return (x == null) - (y == null) || (x < y ? -1 : x > y ? 1 : 0) * o.dir; });
  }
  const plantilla = cols.map((c) => c[5] || 'minmax(0,1fr)').join(' ');
  const fila = (f) => `<div class="tf${f.sel ? ' sel' : ''}${f.acc ? ' cl' : ''}"${f.acc ? ` data-acc="${f.acc}" data-v="${esc(f.val)}"` : ''}${f.title ? ` title="${esc(f.title)}"` : ''}>`
    + cols.map(([k, , cls, fmt]) => `<span class="${cls || ''}${f.cls && f.cls[k] ? ' ' + f.cls[k] : ''}"${f.tip && f.tip[k] ? ` title="${esc(f.tip[k])}"` : ''}>${fmt ? fmt(f.v[k], f) : esc(f.v[k] ?? '')}</span>`).join('') + '</div>';
  // Las filas se dibujan de a TANDA y se suman al llegar abajo: «Documento»
  // con doce meses son 2.500 filas, y dibujarlas todas era 1 s por clic.
  // La fila elegida entra en la primera tanda aunque esté más abajo.
  const iSel = filas.findIndex((f) => f.sel);
  const hasta = Math.max(TANDA, iSel + 20);
  G.tandas[id] = { filas: filas.slice(hasta), fila };
  let h = `<div class="tb ${opts.cls || ''}" style="--cols:${plantilla}"><div class="tf th">`
    + cols.map(([k, r, cls, , ay]) => `<button class="${cls || ''}" data-acc="ordenar" data-v="${id}|${k}" title="${esc(ay || '')}">${esc(r)}${o && o.col === k ? (o.dir > 0 ? ' ↑' : ' ↓') : ''}</button>`).join('')
    + `</div><div class="tl" data-tanda="${id}">`;
  h += filas.slice(0, hasta).map(fila).join('');
  if (!filas.length) h += '<div class="vacio">Nada que mostrar.</div>';
  h += '</div>';
  if (total) h += '<div class="tf tt">' + cols.map(([k, , cls]) => `<span class="${cls || ''}">${esc(total[k] ?? '')}</span>`).join('') + '</div>';
  return h + '</div>';
}
const fS2 = (v) => (finito(v) ? s2(v) : '—');
const fPct = (v) => (finito(v) ? `${num(v * 100, 1)}%` : '');
const fEnt = (v) => (finito(v) ? num(Math.round(v), 0) : '');
const fCompacto = (v) => (!finito(v) || v === 0 ? '—' : fmtK(v));
const fVar = (v, f) => { if (!finito(v)) return esc(f.vtxt || '—'); const [t] = fmtVariacion(v); return t; };
const fNc = (v) => (!finito(v) || Math.abs(v) < NC_MINIMO ? '—' : `−S/ ${num(Math.abs(v), 2)}`);

function resumenTotal(F, V, st) {
  const gran = V.gran, n = V.n;
  let lblFila;
  if (gran === 'Semana') lblFila = V.claves.map((k, j) => `${V.lbls[j]} ${anioSemana(k)}`);
  else if (gran === 'Mes') lblFila = V.claves.map((k) => V.rotDe.get(k)[1]);
  else if (gran === 'Día') lblFila = V.hov.map((h) => h.replace(/<[^>]+>/g, ''));
  else if (gran === 'Por documento') {
    lblFila = V.claves.map((k, j) => { const l = V.primera[j]; return `${dmy(V.diaDe[j])} · ${l.docLeg || '—'} · ${trunc(F.provN[l.prov] || '')}`; });
  } else lblFila = V.lbls.slice();
  const totVista = suma(V.tot, (x) => x);
  const conNc = V.ncTot > NC_MINIMO;
  const fam = familiasDe(V.dd, KPI_FAMILIAS - (conNc ? 1 : 0));
  const colsFam = [], datFam = new Map(), totFam = {};
  if (fam.top.length + fam.resto[0] > 1) {
    const por = new Map();
    V.dd.forEach((l) => { const k = `${l.clave}\u0001${l.fam}`; por.set(k, (por.get(k) || 0) + l.v); });
    let acum = V.claves.map(() => 0);
    fam.top.forEach(([f, v], i) => {
      const vals = V.claves.map((k) => por.get(`${k}\u0001${f}`) || 0);
      acum = acum.map((a, j) => a + vals[j]);
      datFam.set(`fam_${i}`, vals); colsFam.push([`fam_${i}`, F.famN[f]]); totFam[`fam_${i}`] = fmtK(v);
    });
    if (fam.resto[0]) {
      const c = `fam_${fam.top.length}`;
      datFam.set(c, V.tot.map((t, j) => Math.max(t - acum[j], 0))); colsFam.push([c, `${fam.resto[0]} más`]); totFam[c] = fmtK(fam.resto[1]);
    }
  }
  const ncEje = V.claves.map((k) => V.ncDe.get(k) || 0);
  const cols = [['periodo', gran === 'Por documento' ? 'Documento' : 'Período', 'nm', null, '', 'minmax(150px,1fr)'],
    ['valor', `Valorizado ${V.rotValor}`, 'r', fS2, 'Valorizado de compra del período', '138px']];
  if (conNc) cols.push(['nc', 'Notas de crédito', 'r', fNc, 'Notas de crédito de proveedores ya restadas del valorizado, en el período de la factura que corrigen. El Resumen de Ingresos del Almacén no las resta', '120px']);
  cols.push(['parte', '% del total', 'r', fPct, '% del total · cuánto pesa esta barra en el total de la vista', '86px']);
  if (GRAN_CON_DOCS.includes(gran)) cols.push(['docs', 'Documentos', 'r', fEnt, 'En cuántos comprobantes se repartió la compra del período', '96px']);
  cols.push(['lineas', 'Líneas', 'r', fEnt, 'Líneas de compra del período', '66px']);
  if (GRAN_VARIACION.includes(gran)) cols.push(['variacion', 'Variación', 'r', fVar, 'Variación contra la barra ANTERIOR del gráfico, no contra el período anterior del calendario', '84px']);
  colsFam.forEach(([c, r]) => cols.push([c, r, 'r', fCompacto, `${r} · valorizado de compra de esa familia en cada barra`, '86px']));
  const filas = V.claves.map((k, j) => {
    const v = { periodo: lblFila[j], valor: V.tot[j], parte: totVista ? V.tot[j] / totVista : 0, docs: V.ndocs[j], lineas: V.nlin[j],
      variacion: V.vars[j] && V.vars[j][0] === 'ok' ? V.vars[j][1] : null, nc: -ncEje[j] };
    colsFam.forEach(([c]) => { v[c] = datFam.get(c)[j]; });
    const tipF = {};
    colsFam.forEach(([c]) => { const x = v[c]; if (x) tipF[c] = `S/ ${num(x, 2)}${V.tot[j] ? ` · ${(x / V.tot[j] * 100).toFixed(1)}% de la barra` : ''}`; });
    tipF.variacion = V.varNota[j];
    if (ncEje[j] > NC_MINIMO) {
      tipF.nc = `Sin restarla: S/ ${num(V.tot[j] + ncEje[j], 2)}, lo que suma el Resumen de Ingresos del Almacén.\n`
        + V.ncd.filter((x) => x.clave === k).map((x) => `${F.notaTxt[x.nota]} · ${F.provN[x.prov]} · sobre ${x.docLeg || F.docs[x.doc]} del ${dmy(x.d)}: −S/ ${num(x.v, 2)}`).join('\n');
    }
    const vt = V.vars[j];
    const cls = {};
    if (vt && vt[0] === 'ok') cls.variacion = fmtVariacion(vt[1])[1] + ' b'; else cls.variacion = 'gr it';
    cls.nc = ncEje[j] > NC_MINIMO ? 'nc' : 'gr';
    return { v, s: { periodo: k }, vtxt: vt && vt[0] === 'parcial' ? 'parcial' : '—', sel: k === st.foco, tip: tipF, cls,
      acc: 'fila-per', val: k, title: 'Clic: sus documentos en Detalle' };
  });
  const total = { periodo: `Total · ${num(n, 0)} ${UNIDAD[gran][n === 1 ? 0 : 1]}`, valor: `S/ ${num(totVista, 2)}`, parte: '100%',
    docs: num(suma(V.ndocs, (x) => x), 0), lineas: num(suma(V.nlin, (x) => x), 0), ...totFam };
  if (conNc) total.nc = `−S/ ${num(V.ncTot, 2)}`;
  return { html: tabla('per', cols, filas, total, st, { cls: 'per' }), pie: `<b>${delAl(V.dd.map((l) => l.d))}</b> · agrupado por ${AGRUPADO[gran]} — una fila por barra, en el orden del eje; un clic en una fila abre sus documentos.`,
    cols, filas };
}

function resumenProveedores(F, V, st) {
  const g = new Map();
  V.dd.forEach((l) => {
    const a = g.get(l.prov) || { prov: l.prov, valor: 0, docs: new Set(), items: new Set() };
    a.valor += l.v; a.docs.add(l.compra); a.items.add(l.prod); g.set(l.prov, a);
  });
  const rows = [...g.values()].sort((a, b) => b.valor - a.valor || pyCmp(F.provs[a.prov], F.provs[b.prov]));
  const tot = suma(rows, (a) => a.valor) || 1;
  const cols = [['prov', 'Proveedor', 'nm', null, '', 'minmax(160px,1fr)'], ['valor', `Valor ${V.rotValor}`, 'r', fS2, 'Valorizado de compra del proveedor en el período', '136px'],
    ['parte', '% del período', 'r', fPct, 'Cuánto pesa el proveedor en el valor total del período', '110px'],
    ['docs', 'Documentos', 'r', fEnt, 'En cuántos comprobantes se le compró', '100px'],
    ['items', 'Ítems distintos', 'r', fEnt, 'Productos distintos que se le compraron en el período', '120px']];
  const filas = rows.map((a) => ({ v: { prov: F.provN[a.prov] || F.provs[a.prov], valor: Math.round(a.valor * 100) / 100, parte: a.valor / tot, docs: a.docs.size, items: a.items.size },
    s: {}, acc: 'prov', val: F.provs[a.prov], title: 'Clic: sus documentos en Detalle' }));
  const total = { prov: `Total · ${num(rows.length, 0)} ${rows.length === 1 ? 'proveedor' : 'proveedores'}`, valor: `S/ ${num(suma(rows, (a) => a.valor), 2)}`,
    parte: '100%', docs: num(suma(rows, (a) => a.docs.size), 0), items: num(new Set(V.dd.map((l) => l.prod)).size, 0) };
  return { html: tabla('provs', cols, filas, total, st, { orden: { col: 'valor', dir: -1 }, cls: 'provs' }),
    pie: `<b>${delAl(V.dd.map((l) => l.d))}</b> · una fila por proveedor — un clic en uno abre sus documentos en Detalle.`, cols, filas };
}

// `igv_de_linea`: «18 %», «exonerado», «guía» u otra tasa.
function igvDeLinea(neto, igv, tipo) {
  if (tipo === 'G') return 'guía';
  if (Math.abs(igv) < 0.005) return 'exonerado';
  if (!(neto > 0)) return '—';
  const t = igv / neto;
  return Math.abs(t - 0.18) < 0.005 ? '18 %' : `${(t * 100).toFixed(1)} %`;
}

function detalle(F, V, st) {
  if (!V.conDetalle) return { html: '', pie: 'Tocá una barra para ver sus documentos.' };
  const gran = V.gran;
  let amb, nombre;
  if (V.provOk) {
    amb = V.ddDet.filter((l) => F.provs[l.prov] === st.provDet);
    nombre = `${F.provN[F.provs.indexOf(st.provDet)]} · ${delAl(amb.map((l) => l.d))}`;
  } else if (gran === 'Por documento') {
    const dia = V.dd.find((l) => l.compra === st.foco).d;
    amb = V.ddDet.filter((l) => l.d === dia);
    nombre = `${cap(DIAS[diaSemana(dia)])} ${dmy(dia)} · las compras del día`;
  } else {
    const id = V.focoOk ? st.foco : V.ddDet.find((l) => l.compra === st.doc).clave;
    amb = V.ddDet.filter((l) => l.clave === id);
    nombre = gran === 'Día' ? V.hov[V.ix.get(id)] : (V.rotDe.get(id) || [null, id])[1];
  }
  const g = new Map();
  amb.forEach((l) => {
    const a = g.get(l.compra) || { compra: l.compra, fecha: l.d, doc: l.docLeg, prov: l.prov, lineas: 0, valor: 0, neto: 0, igv: 0, tipo: l.tipo, usd: l.usd };
    a.fecha = Math.min(a.fecha, l.d); a.lineas += 1; a.valor += l.v; a.neto += l.neto; a.igv += l.igv;
    g.set(l.compra, a);
  });
  const docs = [...g.values()].sort((a, b) => b.valor - a.valor || pyCmp(a.compra, b.compra));
  if (!docs.length) return { html: '<div class="vacio">Sin documentos.</div>', pie: '' };
  let sel;
  if (V.docOk && g.has(st.doc)) sel = st.doc;
  else if (gran === 'Por documento' && !V.provOk) sel = st.foco;
  else sel = docs[0].compra;
  const marca = (a) => (a.tipo === 'G' ? 'guía · ' : a.tipo === 'N' ? 'NC · ' : a.usd ? 'US$ · ' : '');
  const colsD = [];
  if (gran !== 'Por documento') colsD.push(['fecha', 'Fecha', '', (v) => dmy(v), '', '86px']);
  if (F.hayDoc) colsD.push(['doc', 'Documento', 'nm', null, '', '118px']);
  colsD.push(['prov', 'Proveedor', 'nm', null, '', 'minmax(80px,1fr)'], ['neto', 'Neto', 'r', fS2, 'Valor sin IGV', '96px'],
    ['igv', 'IGV', 'r', fS2, 'El IGV del documento. Vacío en una guía: todavía no lo lleva', '84px'],
    ['total', 'Total', 'r', fS2, 'Neto + IGV: lo que dice el papel', '96px']);
  const filasD = docs.map((a) => ({ v: { fecha: a.fecha, doc: marca(a) + (a.doc || '—'), prov: F.provN[a.prov] || F.provs[a.prov], neto: a.neto,
    igv: a.tipo === 'G' ? null : a.igv, total: a.neto + a.igv }, s: { fecha: a.fecha }, sel: a.compra === sel, acc: 'doc', val: a.compra,
    tip: { doc: marca(a) + (a.doc || '—'), prov: F.provN[a.prov] }, title: 'Clic: sus líneas al costado' }));
  const nNc = docs.filter((a) => a.tipo === 'N').length, nD = docs.length - nNc;
  const totD = { fecha: '', doc: '', prov: `${nD} compra${nD === 1 ? '' : 's'}` + (nNc ? ` · ${nNc} NC` : ''),
    neto: `S/ ${num(suma(docs, (a) => a.neto), 2)}`, igv: `S/ ${num(suma(docs, (a) => a.igv), 2)}`, total: `S/ ${num(suma(docs, (a) => a.neto + a.igv), 2)}` };
  const colRot = gran !== 'Por documento' ? 'fecha' : (F.hayDoc ? 'doc' : null);
  if (colRot) totD[colRot] = 'Total'; else totD.prov = `Total · ${totD.prov}`;
  const lin = amb.filter((l) => l.compra === sel);
  const colsL = [['prod', 'Producto', 'nm', null, '', 'minmax(80px,1fr)'], ['cant', 'Cantidad', 'r', (v) => (finito(v) ? num(v, 1) : ''), '', '78px'],
    ['punit', 'P. unit.', 'r', fS2, 'Precio unitario sin IGV', '84px'], ['valor', 'Valor sin IGV', 'r', fS2, '', '104px'],
    ['igv', 'IGV', '', null, 'Qué IGV paga el producto: 18 %, exonerado (verduras, pescados, frutas) o guía (todavía sin IGV: lo trae la factura)', '72px']];
  const filasL = lin.map((l) => ({ v: { prod: F.prods[l.prod], cant: l.cant, punit: l.punit, valor: l.neto, igv: igvDeLinea(Math.abs(l.neto), Math.abs(l.igv), l.tipo) },
    s: {}, tip: { prod: F.prods[l.prod] } }));
  const totL = { prod: `Total · ${lin.length} línea${lin.length === 1 ? '' : 's'}`, valor: `S/ ${num(suma(lin, (l) => l.neto), 2)}` };
  return { html: `<div class="det">${tabla('docs', colsD, filasD, totD, st, { orden: { col: 'neto', dir: -1 }, cls: 'docs' })}`
    + `${tabla('lin', colsL, filasL, totL, st, { orden: { col: 'valor', dir: -1 }, cls: 'lin' })}</div>`,
  pie: `<b>${esc(nombre.replace(/<[^>]+>/g, ''))}</b> — clic en una compra para ver sus líneas al costado.`, colsD, filasD, colsL, filasL };
}

// ── Los filtros de la cabecera: un menú con buscador y casillas ─────────
const FILTROS = [['fam', 'Familia', 'Todas las familias', 'familias'], ['sub', 'Subfamilia', 'Todas las subfamilias', 'subfamilias'],
  ['prov', 'Proveedor', 'Todos los proveedores', 'proveedores'], ['prod', 'Producto', 'Todos los productos', 'productos']];
function opcionesDe(V, k) { return { fam: V.famOps, sub: V.subOps, prov: V.provOps, prod: V.prodOps }[k] || []; }
function listaMenu(F, V, st, k) {
  const q = st.q[k] || '', sel = new Set(st[k]);
  const nom = (o) => (k === 'prov' ? (F.provN[F.provs.indexOf(o)] || o) : k === 'fam' ? F.famN[F.fams.indexOf(o)] || o : o);
  const ops = opcionesDe(V, k).filter((o) => !q || coincide(nom(o), q));
  return ops.slice(0, 400).map((o) => `<label><input type="checkbox" data-acc="filtro" data-k="${k}" data-v="${esc(o)}"${sel.has(o) ? ' checked' : ''}> ${esc(nom(o))}</label>`).join('')
    + (ops.length > 400 ? `<p class="mas">y ${ops.length - 400} más: escribí para buscar</p>` : '') + (!ops.length ? '<p class="mas">Sin coincidencias.</p>' : '');
}
function cabecera(F, V, st) {
  const disp = { fam: F.hayFam && V.famOps.length, sub: F.haySub && V.subOps.length, prov: F.hayProv, prod: true };
  const fil = FILTROS.filter(([k]) => disp[k]).map(([k, rot, todas, plural]) => {
    const s = st[k];
    const nom = (o) => (k === 'prov' ? (F.provN[F.provs.indexOf(o)] || o) : k === 'fam' ? F.famN[F.fams.indexOf(o)] || o : o);
    const txt = !s.length ? todas : s.length === 1 ? `${rot}: ${nom(s[0])}` : `${s.length} ${plural}`;
    return `<div class="ms"><button class="ms-b${s.length ? ' on' : ''}" data-acc="menu" data-v="${k}" title="${esc(s.map(nom).join(', '))}">${esc(txt)} <i>▾</i></button>`
      + (st.menu === k ? `<div class="ms-l"><input class="ms-q" data-k="${k}" placeholder="Buscar…" value="${esc(st.q[k] || '')}" autocomplete="off">`
        + `<div class="ms-o">${listaMenu(F, V, st, k)}</div>${s.length ? `<button class="ms-x" data-acc="limpiar" data-v="${k}">Quitar el filtro</button>` : ''}</div>` : '') + '</div>';
  }).join('');
  return `<div class="cab"><div class="seg">${GRANOS.map(([k, t]) => `<button class="${k === st.gran ? 'on' : ''}" data-acc="gran" data-v="${k}">${t}</button>`).join('')}</div>`
    + `<div class="fils">${fil}</div><span class="lugar-fecha" aria-hidden="true"></span></div>`
    + `<div class="docrow"><span class="rot">Documento</span><div class="seg chico">${DOCUS.map((k) => `<button class="${k === st.docu ? 'on' : ''}" data-acc="docu" data-v="${k}">${k}</button>`).join('')}</div>`
    + `<span class="rot dos">Montos</span><div class="seg chico">${MONTOS.map((k) => `<button class="${k === st.montos ? 'on' : ''}" data-acc="montos" data-v="${k}">${k}</button>`).join('')}</div>`
    + '<span class="nota">Sólo esta tarjeta · «Todos» es lo que suman los reportes de ingresos del Almacén, menos las notas de crédito</span></div>';
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function pintar() {
  const raiz = G.raiz, F = G.F, st = G.st;
  if (!raiz || !F) return;
  // Cambiar el grano, un filtro o Documento suelta el foco (el `_ctx` de antes).
  const ctx = JSON.stringify([st.gran, st.fam, st.sub, st.prov, st.prod, st.docu]);
  if (st.ctx !== ctx) { st.ctx = ctx; st.foco = null; st.doc = null; }
  const V = calcular(F, st);
  G.V = V;
  const W = raiz.clientWidth || 1150, H = raiz.clientHeight || 540;
  let html = cabecera(F, V, st);
  if (V.vacio) {
    raiz.innerHTML = html + `<div class="vacio grande"><b>${esc(V.titulo)}</b> — sin compras que mostrar. Ampliá el rango de fechas (arriba a la derecha) o soltá algún filtro de la tarjeta.</div>`;
    return;
  }
  // El renglón del título: título, «Partir por» y lo resaltado (#620, #621).
  html += `<div class="tit"><span class="t">${esc(V.titulo)}<small>${esc(V.sufijo)}</small></span>`;
  if (V.opsPartir.length) {
    const apagado = !GRAN_PARTIDA.includes(st.gran);
    html += `<div class="seg chico${apagado ? ' off' : ''}">${V.opsPartir.map((k) => `<button class="${k === st.partir ? 'on' : ''}" data-acc="partir" data-v="${k}"${apagado ? ' disabled title="En «Documento» la barra ya es una compra"' : ''}>${k}</button>`).join('')}</div>`;
  }
  if (V.opsRes.length) {
    const colorDe = new Map(V.partes.map(([r, c]) => [r, c]));
    html += '<div class="res">' + V.opsRes.map((r) => `<button class="pill${r === V.resaltado ? ' on' : ''}" data-acc="resaltar" data-v="${esc(r)}" title="${esc(r)}" style="--c:${colorDe.get(r)}">${esc(trunc(r, 14))}</button>`).join('') + '</div>';
  }
  html += '</div>';
  const fijo = 32 + 26 + 30 + 30 + 5 * 6;
  const libre = Math.max(200, H - fijo);
  const altoG = V.conTabla ? Math.max(150, Math.min(300, Math.round(libre * 0.46))) : libre - 6;
  const gr = grafico(F, V, st, W, altoG);
  G.X = gr.X; G.W = W;
  html += `<div class="graf" style="height:${altoG}px">${gr.svg}<div class="tip" hidden></div></div>`;
  if (V.n === 1) html += '<p class="aviso1">Sólo hay compras en un período dentro del rango de fechas activo (arriba) — ampliá el rango para ver la evolución.</p>';
  // La fila del modo y la zona de abajo.
  let zona;
  if (st.modo === 'Resumen Total') zona = resumenTotal(F, V, st);
  else if (st.modo === 'Resumen del Período') zona = resumenProveedores(F, V, st);
  else zona = detalle(F, V, st);
  G.zona = zona;
  html += `<div class="pie"><div class="seg chico">${MODOS.map((k) => `<button class="${k === st.modo ? 'on' : ''}" data-acc="modo" data-v="${k}">${k}</button>`).join('')}</div>`
    + `<span class="cap">${zona.pie}</span><button class="excel" data-acc="excel" title="Baja la tabla tal como se ve">Excel</button></div>`
    + `<div class="zona">${zona.html}</div>`;
  const listas = [...raiz.querySelectorAll('.tl')].map((e) => e.scrollTop);
  const q = raiz.querySelector('.ms-q:focus');
  raiz.innerHTML = html;
  [...raiz.querySelectorAll('.tl')].forEach((e, i) => { if (listas[i]) e.scrollTop = listas[i]; });
  if (q) { const n = raiz.querySelector(`.ms-q[data-k="${q.dataset.k}"]`); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }
  // La fecha es un botón de Python en la misma página: la cabecera le deja su ancho.
  const fb = document.querySelector('.st-key-cp_sem_fecha');
  if (fb && fb.offsetWidth) raiz.style.setProperty('--cp-fecha', `${fb.offsetWidth + 12}px`);
}

function pintarTip(i) {
  const raiz = G.raiz, t = raiz && raiz.querySelector('.tip');
  if (!t || !G.V) return;
  if (i == null) { t.hidden = true; return; }
  t.innerHTML = tip(G.F, G.V, G.st, i);
  t.hidden = false;
  const tw = t.offsetWidth || 260, x = G.X(i);
  t.style.left = `${x + 14 + tw <= G.W ? x + 14 : Math.max(0, x - 14 - tw)}px`;
}

function excel() {
  const V = G.V, z = G.zona, st = G.st;
  if (!V || V.vacio || !z) return;
  const plano = (s) => String(s ?? '').replace(/<[^>]+>/g, '');
  const hoja = (nombre, cols, filas) => ({ nombre, cabeza: cols.map((c) => c[1]),
    filas: filas.map((f) => cols.map(([k]) => { const v = f.v[k]; return typeof v === 'number' && k !== 'fecha' ? v : (k === 'fecha' && finito(v) ? dmy(v) : plano(v)); })) });
  let hojas;
  if (st.modo === 'Detalle' && z.colsD) hojas = [hoja('Documentos', z.colsD, z.filasD), hoja('Líneas', z.colsL, z.filasL)];
  else if (z.cols) hojas = [hoja(st.modo, z.cols, z.filas)];
  else return;
  bajar(`compras_por_periodo_${archivo(st.modo)}_${iso(G.F.R0)}_${iso(G.F.R1)}.xlsx`, libro(hojas));
}

// ── Los clics ────────────────────────────────────────────────────────────
function accion(acc, val, el) {
  const st = G.st, V = G.V;
  if (acc !== 'menu' && acc !== 'filtro') st.menu = null;
  if (acc === 'gran') st.gran = val;
  else if (acc === 'menu') { st.menu = st.menu === val ? null : val; }
  else if (acc === 'filtro') {
    const k = el.dataset.k, xs = st[k];
    st[k] = el.checked ? [...xs, val] : xs.filter((x) => x !== val);
  } else if (acc === 'limpiar') { st[val] = []; st.menu = null; }
  else if (acc === 'docu') st.docu = val;
  else if (acc === 'montos') st.montos = val;
  else if (acc === 'partir') st.partir = val;
  else if (acc === 'resaltar') st.res[st.partir] = st.res[st.partir] === val ? null : val;
  else if (acc === 'modo') st.modo = val;
  else if (acc === 'barra' || acc === 'fila-per') {
    const k = acc === 'barra' ? V.claves[+val] : val;
    st.provDet = null;
    if (st.modo !== 'Detalle') { st.doc = null; st.foco = k; st.modo = 'Detalle'; } else if (st.doc) { st.doc = null; st.foco = k; } else st.foco = st.foco === k ? null : k;
  } else if (acc === 'prov') { st.provDet = val; st.foco = null; st.doc = null; st.modo = 'Detalle'; }
  else if (acc === 'doc') {
    if (V.gran === 'Por documento' && !V.provOk) st.foco = val; else st.doc = val;
  } else if (acc === 'ordenar') {
    const [id, col] = val.split('|'), o = st.orden[id];
    st.orden[id] = !o || o.col !== col ? { col, dir: -1 } : o.dir < 0 ? { col, dir: 1 } : null;
  } else if (acc === 'excel') { excel(); return; }
  else return;
  pintar();
}
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.disabled) return;
    if (b.dataset.acc === 'filtro' && b.tagName !== 'INPUT') return;
    accion(b.dataset.acc, b.dataset.v, b);
  });
  raiz.addEventListener('input', (ev) => {
    const q = ev.target.closest('.ms-q');
    if (!q) return;
    G.st.q[q.dataset.k] = q.value;
    const o = raiz.querySelector('.ms-o');
    if (o) o.innerHTML = listaMenu(G.F, G.V, G.st, q.dataset.k);
  });
  raiz.addEventListener('mouseover', (ev) => {
    const b = ev.target.closest('[data-acc="barra"]');
    if (b && raiz.contains(b)) pintarTip(+b.dataset.v);
  });
  raiz.addEventListener('mouseout', (ev) => {
    const b = ev.target.closest('[data-acc="barra"]');
    if (b && !(ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest('[data-acc="barra"]'))) pintarTip(null);
  });
  // El menú de un filtro se cierra con Escape o con un clic fuera de él,
  // en cualquier parte de la página: al marcar una casilla la pieza se
  // vuelve a dibujar y el foco ya no está adentro.
  if (!G.docEnlazado) {
    G.docEnlazado = true;
    document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && G.st && G.st.menu) { G.st.menu = null; pintar(); } });
    document.addEventListener('pointerdown', (ev) => {
      if (!G.st || !G.st.menu) return;
      // Un control de la pieza lo cierra en su propio clic (redibujar acá
      // borraría el botón antes de que el clic llegue).
      if (ev.composedPath().some((n) => n.classList && (n.classList.contains('ms') || (n.dataset && n.dataset.acc)))) return;
      G.st.menu = null;
      pintar();
    }, true);
  }
  // La tanda siguiente de una tabla larga, al acercarse al final.
  raiz.addEventListener('scroll', (ev) => {
    const l = ev.target;
    if (!l.dataset || !l.dataset.tanda || l.scrollTop + l.clientHeight < l.scrollHeight - 200) return;
    const t = G.tandas[l.dataset.tanda];
    if (!t || !t.filas.length) return;
    l.insertAdjacentHTML('beforeend', t.filas.splice(0, TANDA).map(t.fila).join(''));
  }, true);
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.lineas) return;
  let raiz = parentElement.querySelector('.cpp');
  const nueva = !raiz;
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'cpp';
    parentElement.appendChild(raiz);
    enlazar(raiz);
    let ancho = 0, espera = 0;
    new ResizeObserver(() => {
      if (Math.abs(raiz.clientWidth - ancho) < 2) return;
      ancho = raiz.clientWidth;
      clearTimeout(espera);
      espera = setTimeout(() => { if (G.F) pintar(); }, 120);
    }).observe(raiz);
  }
  G.raiz = raiz;
  if (!G.st) G.st = estadoInicial();
  // La misma vista de la corrida anterior: redibujar no cambia nada.
  if (!nueva && G.F && G.F.sello === data.sello) return;
  G.F = leer(data);
  pintar();
}
