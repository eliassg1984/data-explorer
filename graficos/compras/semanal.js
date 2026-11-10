// Compras › «Compras por período» (reglas #716 y #770: una pantalla, cuatro
// indicadores, una zona por pestaña y la lista al costado).
//
// La monta graficos/compras/semanal.py con st.components.v2 (sin iframe,
// estilos en un shadow root). `_xlsx.js` va antepuesto (libro, bajar,
// archivo), y `ficha_familias.js` (`FichaFam`, la ficha del filtro de
// familias de la vista, regla #843). Python manda las líneas del rango (de TODOS los documentos, con
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
const RL = { dia: 0, prod: 1, prov: 2, doc: 3, fam: 4, sub: 5, cant: 6, neto: 7, igv: 8, tipo: 9, usd: 10, punit: 11, refT: 12, refS: 13, fl: 14 };
const RN = { nota: 12, diaNc: 13 };
const TIPOS = ['F', 'G', 'O'];
const GRANOS = [['Día', 'Día'], ['Semana', 'Semana'], ['Mes', 'Mes'], ['Año', 'Año'], ['Por documento', 'Documento']];
const MODOS = ['Resumen Total', 'Resumen del Período', 'Detalle'];
const DOCUS = ['Todos', 'Facturas', 'Guías sin canjear'];
const MONTOS = ['Sin IGV', 'Con IGV'];
const FAM = 'Familia', SUB = 'Subfamilia', PROV = 'Proveedor', PRECIO = 'Precio';
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
// «▼ 26 %»: comprar menos no es bueno ni malo; el color queda para el precio.
const flecha = (t) => (t.startsWith('+') ? `▲ ${t.slice(1).replace('%', ' %')}` : t.startsWith('−') ? `▼ ${t.slice(1).replace('%', ' %')}` : t.replace('%', ' %'));
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
  const L = data.lineas.map((r, i) => ({ ...fila(r, i), refT: r[RL.refT], refS: r[RL.refS], fl: r[RL.fl] || 0 }));
  // Lo que se compra para comparar (regla #770): por día, producto y proveedor.
  const C = (data.contra || []).map((r) => ({ d: base + r[0], prod: r[1], prov: r[2], fam: r[3], sub: r[4], tipo: TIPOS[r[5]] || 'O', neto: r[6] || 0, igv: r[7] || 0 }));
  const N = (data.notas || []).map((r, i) => ({ ...fila(r, i), nota: r[RN.nota], dNc: base + r[RN.diaNc] }));
  const feriados = new Set((data.feriados || []).map(dn));
  const famSubs = new Map(Object.entries(data.fam_subs || {}).map(([k, v]) => [Number(k), v]));
  return { sello: data.sello, R0: dn(data.rango[0]), R1: dn(data.rango[1]), feriados, L, N, C, desde: data.contra_desde ? dn(data.contra_desde) : null,
    meses: data.meses || [], familias: data.familias || null, ordFam: data.ord_fam || [], nOrdFam: data.n_ord_fam || 0,
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
  if (F.familias?.en_panel) { st.fam = []; st.sub = []; }
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
  const opsPartir = [[FAM, F.hayFam], [SUB, F.haySub], [PROV, F.hayProv], [PRECIO, F.hayCant]].filter((x) => x[1]).map((x) => x[0]);
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
  if (partidaGran && st.partir === FAM) {
    partes = partesColumna(dd, 'fam', claves, F.ordFam, F.nOrdFam, 'Otras', (x) => F.famN[x]);
    titPartes = 'Por familia';
  } else if (partidaGran && st.partir === SUB) {
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

  // El efecto del precio y lo marcado para revisar (regla #770): las cuentas de
  // `producto._resumen`, sin las líneas marcadas y siempre en neto.
  const refDe = (l) => (docu === 'Todos' ? l.refT : l.refS);
  const efProd = new Map(), efBarra = new Map(), revBarra = claves.map(() => 0), revProd = new Set();
  let revLin = 0, revVal = 0;
  dd.forEach((l) => {
    const j = ix.get(l.clave);
    if (l.fl) { revBarra[j] += l.v; revLin += 1; revVal += l.v; revProd.add(l.prod); return; }
    const ref = refDe(l);
    if (!(l.cant > 0) || !finito(ref)) return;
    const e = l.neto - ref * l.cant, k = `${j}\u0001${l.prod}`;
    efProd.set(l.prod, (efProd.get(l.prod) || 0) + e);
    efBarra.set(k, (efBarra.get(k) || 0) + e);
  });
  const sube = [...efProd.values()].filter((v) => v >= 1), baja = [...efProd.values()].filter((v) => v <= -1);
  V.efecto = { up: suma(sube, (x) => x), dn: suma(baja, (x) => x), nUp: sube.length, nDn: baja.length, porProd: efProd };
  const efUp = claves.map(() => 0), efDn = claves.map(() => 0);
  efBarra.forEach((v, k) => { const j = Number(k.split('\u0001')[0]); if (v > 0) efUp[j] += v; else efDn[j] += v; });
  Object.assign(V, { efUp, efDn, revBarra, revProd: revProd.size, revLin, revVal });
  // Lo mismo un año o un período antes, día por día.
  const cDia = new Map();
  filtrar(F.C.filter((l) => okTipo(l.tipo))).forEach((l) => cDia.set(l.d, (cDia.get(l.d) || 0) + l.neto + (conIgv ? l.igv : 0)));
  const sumaDias = (a, b) => { let t = 0; for (let x = a; x <= b; x += 1) t += cDia.get(x) || 0; return t; };
  const enBase = (a) => F.desde != null && a >= F.desde;
  const anoAntes = (x) => { const [y, m, d] = ymd(x); return Math.min(Date.UTC(y - 1, m - 1, d), Date.UTC(y - 1, m, 0)) / DIA; };
  const atras = (a, b) => {
    if (st.contra === 'ant') { const n2 = b - a + 1; return [a - n2, b - n2]; }
    if (gran === 'Día' || gran === 'Semana') return [a - 364, b - 364];
    return [anoAntes(a), anoAntes(b)];
  };
  V.ghost = claves.map((k) => {
    if (st.contra === 'no' || gran === 'Por documento' || !F.C.length) return null;
    const [i0, f0] = limites(k, gran), a = Math.max(i0, F.R0), b2 = Math.min(f0, F.R1), [ca, cb] = atras(a, b2);
    return enBase(ca) ? sumaDias(ca, cb) : null;
  });
  const [ka, kb] = st.contra === 'ano' ? [anoAntes(F.R0), anoAntes(F.R1)] : [F.R0 - (F.R1 - F.R0 + 1), F.R0 - 1];
  V.contraTot = st.contra === 'no' || !enBase(ka) ? null : sumaDias(ka, kb);
  V.contraNom = `${ymd(ka)[2]} ${MES[ymd(ka)[1] - 1]} – ${ymd(kb)[2]} ${MES[ymd(kb)[1] - 1]}${ymd(kb)[0] !== ymd(F.R1)[0] ? ` de ${ymd(kb)[0]}` : ''}`;
  V.atras = atras; V.enBase = enBase; V.sumaDias = sumaDias;

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

window.__cpPerCalc = { leer, calcular, valorDe, rotuloPeriodo, variaciones, partesColumna, partesPrecio, familiasDe,
  detalleConNotas, planEtiquetas, clave, semanaIso, coloresEstables };

function valorDe(V, st, j) { return st.med === 'docs' ? V.ndocs[j] : st.med === 'precio' ? V.efUp[j] + V.efDn[j] : st.med === 'revisar' ? V.revBarra[j] : V.tot[j]; }

const G = window.__cpPer || (window.__cpPer = { st: null, F: null, raiz: null });
G.tandas = G.tandas || {};
const estadoInicial = () => ({ gran: 'Semana', fam: [], sub: [], prov: [], prod: [], docu: 'Todos', montos: 'Sin IGV',
  partir: FAM, res: { [FAM]: null, [SUB]: null, [PROV]: null, [PRECIO]: null }, modo: 'Resumen Total', foco: null, doc: null, provDet: null, menu: null, q: {}, orden: {}, ctx: '',
  filtrosAbiertos: false, lectura: null, zona: 'graf', med: 'valor', contra: 'ano', item: null, kAb: false });
// Los tonos de «Partir por», del acento al gris, en el orden de la lista.
const TONOS = ['var(--cp-t0)', 'var(--cp-t1)', 'var(--cp-t2)', 'var(--cp-t3)', 'var(--cp-t4)', 'var(--cp-t5)'];
const colorParte = (V, k) => (/^(Otras|Otros) \(/.test(V.partes[k][0]) ? 'var(--cp-otro)' : G.st.partir === PRECIO ? V.partes[k][1] : TONOS[k % TONOS.length]);
const esMovil = () => window.matchMedia('(max-width: 900px)').matches;

// ── El gráfico ───────────────────────────────────────────────────────────
function grafico(F, V, st, W, H) {
  const n = V.n, gran = V.gran;
  const diario = gran === 'Día' || gran === 'Por documento';
  // Los días del eje y sus tramos contiguos (`_grupos_de_dia`).
  const grupos = [];
  if (diario) V.diaDe.forEach((d, i) => { const g = grupos[grupos.length - 1]; if (g && g[2] === d) g[1] = i; else grupos.push([i, i, d]); });
  const PL = 8, PR = 8, PB = 32;
  const plotW0 = Math.max(60, W - PL - PR);
  const pxDia = diario ? plotW0 / Math.max(grupos.length, 1) : 0;
  const ferIx = diario && pxDia >= PX_DIA_BANDA ? grupos.map((g, j) => (F.feriados.has(g[2]) ? j : -1)).filter((j) => j >= 0) : [];
  const PT = ferIx.length ? 18 : 8;
  const plotW = plotW0, plotH = Math.max(40, H - PT - PB);
  const slot = plotW / n, bw = Math.max(1, slot * 0.8);
  const X = (i) => PL + (i + 0.5) * slot;
  const tot = V.tot;
  // En móvil sólo el total y siempre horizontal. El desglose se consulta
  // tocando la barra; no se achica ni se gira para hacerlo entrar.
  const movil = esMovil();
  const med = st.med || 'valor', vals = tot.map((t, j) => valorDe(V, st, j));
  const fmtMed = (v) => (med === 'docs' ? num(v, 0) : med === 'precio' ? `${v > 0.5 ? '+' : v < -0.5 ? '−' : ''}S/ ${num(Math.abs(v), 0)}` : fmtK(v));
  // Una sola cifra en cada barra (regla #770): lo demás, en la tabla y al pasar el cursor.
  const reng = vals.map((v) => (v ? [[fmtMed(v), esc(fmtMed(v))]] : []));
  const plan = planEtiquetas(reng, slot, plotH, F.techo);
  const [forma, k, altoEtq] = movil && plan[0] !== 'derecha' ? [null, 0, 0] : plan;
  const conGhost = med === 'valor' && V.ghost.some((x) => x != null);
  const hi = Math.max(0, ...(med === 'precio' ? V.efUp : vals), ...(conGhost ? V.ghost.map((x) => x || 0) : [])), lo = med === 'precio' ? Math.min(0, ...V.efDn) : 0;
  let y0 = lo, y1 = hi || 1;
  if (forma) { const a = Math.min(altoEtq, plotH * F.techo); y1 = lo + (hi - lo) * plotH / (plotH - a); } else y1 = hi * 1.06 || 1;
  const Y = (v) => PT + plotH - (v - y0) / (y1 - y0) * plotH;
  const redondo = (r) => { const b = Math.pow(10, Math.floor(Math.log10(r || 1))); const f = r / b; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * b; };
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
    svg += `<line class="gl" x1="${PL}" x2="${W - PR}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/>`;
  }
  // Las barras: las partes apiladas en tonos, o una sola medida, con el año
  // pasado en gris al lado (regla #770).
  const anchoB = conGhost ? slot * 0.5 : bw, xB = (i) => (conGhost ? X(i) - anchoB / 2 + slot * 0.13 : X(i) - bw / 2);
  const parciales = V.claves.map((k) => { const [a, b] = cobertura(k, gran, V.rango); return gran !== 'Por documento' && gran !== 'Día' && a < b; });
  svg += '<defs><pattern id="cp-rayas" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="7" fill="var(--bg-card)" opacity=".3"/></pattern></defs>';
  const barra = (i, a, b, fill, cls = '') => {
    const top = Math.min(Y(a), Y(b)), h = Math.max(0.5, Math.abs(Y(a) - Y(b)));
    return `<rect class="bar ${cls}" x="${xB(i).toFixed(1)}" y="${top.toFixed(1)}" width="${anchoB.toFixed(1)}" height="${h.toFixed(1)}" style="fill:${fill}"/>`;
  };
  V.claves.forEach((k, i) => {
    const dim = st.foco != null && st.foco !== k ? ' dim' : '';
    if (conGhost && V.ghost[i] != null && V.ghost[i] > 0) {
      const top = Y(V.ghost[i]);
      svg += `<rect class="bar-g${dim}" x="${(xB(i) - slot * 0.26).toFixed(1)}" y="${top.toFixed(1)}" width="${(slot * 0.22).toFixed(1)}" height="${(Y(0) - top).toFixed(1)}"/>`;
    }
    if (med === 'precio') { svg += barra(i, 0, V.efUp[i], 'var(--cp-sube)', dim) + barra(i, 0, V.efDn[i], 'var(--cp-baja)', dim); return; }
    if (med === 'docs' || med === 'revisar') { if (vals[i]) svg += barra(i, 0, vals[i], med === 'revisar' ? 'var(--cp-revisa)' : 'var(--cp-t1)', dim); return; }
    if (!tot[i]) return;
    if (!V.partida) { svg += barra(i, 0, tot[i], 'var(--cp-t1)', dim); return; }
    let acu = 0;
    const orden = V.pila && V.pila.length ? V.pila : V.partes.map((p, q) => q);
    orden.forEach((q) => {
      const y = V.partes[q][2][i];
      if (!y) return;
      const apagada = V.kRes != null && q !== V.kRes;
      svg += barra(i, acu, acu + y, apagada ? 'var(--cp-apagado)' : colorParte(V, q), dim);
      acu += y;
    });
    if (parciales[i]) svg += `<rect x="${xB(i).toFixed(1)}" y="${Y(tot[i]).toFixed(1)}" width="${anchoB.toFixed(1)}" height="${(Y(0) - Y(tot[i])).toFixed(1)}" fill="url(#cp-rayas)" pointer-events="none"/>`;
  });
  if (med === 'precio') svg += `<line class="cero-l" x1="${PL}" x2="${W - PR}" y1="${Y(0).toFixed(1)}" y2="${Y(0).toFixed(1)}"/>`;
  // Las etiquetas.
  if (forma) {
    reng.forEach((r, i) => {
      if (!r.length) return;
      const ls = r.slice(0, k), yTop = Y(med === 'precio' ? V.efUp[i] : Math.max(vals[i], 0)) - 3, x = conGhost ? xB(i) + anchoB / 2 : X(i);
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
  if (!ticks && movil && gran === 'Semana') {
    const cada = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(plotW / 48))));
    ticks = V.claves.flatMap((c, i) => {
      if (i % cada) return [];
      const [a, b] = limites(c, gran), ini = Math.max(a, F.R0), fin = Math.min(b, F.R1);
      const [, m, d] = ymd(ini), [, mf, df] = ymd(fin);
      return [[X(i), ini === fin ? String(d) : `${d}–${df}`, m === mf ? MES[m - 1] : `${MES[m - 1]}–${MES[mf - 1]}`]];
    });
  }
  if (!ticks) {
    // En «Día» con muchos días el rótulo es «24 jul» y no la clave ISO.
    const rot = gran === 'Día' ? V.diaDe.map((d) => { const [, m, dd] = ymd(d); return `${dd} ${MES[m - 1]}`; }) : V.lbls;
    const largo = gran === 'Semana' ? 11 : Math.max(1, ...rot.map((l) => l.length));
    const caben = Math.max(1, Math.floor(plotW / (largo * TICK_PX + TICK_AIRE)));
    const cada = Math.max(1, Math.ceil(n / caben));
    let ult = null;
    ticks = [];
    for (let i = 0; i < n; i += cada) {
      let sub = '', txt = rot[i];
      if (gran === 'Semana') {
        const a = anioSemana(V.claves[i]); if (a !== ult && ult !== null) sub = a; ult = a;
        const [p, q] = limites(V.claves[i], gran), ini = Math.max(p, F.R0), fin = Math.min(q, F.R1), [, m, d] = ymd(ini), [, mf, df] = ymd(fin);
        txt = ini === fin ? `${d} ${MES[m - 1]}` : m === mf ? `${d}–${df} ${MES[m - 1]}` : `${d} ${MES[m - 1]}–${df} ${MES[mf - 1]}`;
      }
      ticks.push([X(i), txt + (parciales[i] ? '*' : ''), sub]);
    }
  }
  ticks.forEach(([x, a, b]) => {
    svg += `<text class="tx" x="${x.toFixed(1)}" y="${PT + plotH + 14}" text-anchor="middle">${esc(a)}</text>`;
    if (b) svg += `<text class="tx sub" x="${x.toFixed(1)}" y="${PT + plotH + 26}" text-anchor="middle">${esc(b)}</text>`;
  });
  for (let i = 0; i < n; i += 1) svg += `<rect class="hit" role="button" tabindex="0" aria-label="${esc(V.hov[i].replace(/<[^>]+>/g, ''))}: ${esc(s2(tot[i]))}" data-acc="barra" data-v="${i}" x="${(PL + i * slot).toFixed(1)}" y="${PT}" width="${slot.toFixed(1)}" height="${plotH}"></rect>`;
  return { svg: svg + '</svg>', X };
}

// El hover de una barra (el `hovertemplate` de antes).
function tip(F, V, st, i) {
  const t = V.tot[i];
  const docs = ` · ${num(V.ndocs[i], 0)} doc${V.ndocs[i] === 1 ? '' : 's'}`;
  let h = `<b>${V.hov[i]}</b>`;
  const gh = V.ghost && V.ghost[i];
  if (gh != null) { const [txt, c] = gh > 0 ? fmtVariacion((t - gh) / gh * 100) : ['—', 'cero']; h += `<br>${st.contra === 'ano' ? 'Año pasado' : 'Período anterior'}: S/ ${num(gh, 2)} · <b class="${c}">${txt}</b>`; }
  if (st.med === 'precio') { const e = V.efUp[i] + V.efDn[i]; h += `<br>Subieron: +S/ ${num(V.efUp[i], 0)} · bajaron: −S/ ${num(Math.abs(V.efDn[i]), 0)}<br><b>Efecto: ${e > 0 ? '+' : e < 0 ? '−' : ''}S/ ${num(Math.abs(e), 0)}</b>`; }
  if (st.med === 'revisar' && V.revBarra[i]) h += `<br>Para revisar: S/ ${num(V.revBarra[i], 2)}`;
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
  // Lo que necesita para leerse: si no entra en la zona, se desliza de lado.
  const minimo = cols.reduce((s, c) => s + Number((/(\d+)px/.exec(c[5] || '') || [0, 90])[1]) + 8, 16);
  let h = `<div class="tb ${opts.cls || ''}" style="--cols:${plantilla};min-width:${minimo}px"><div class="tf th">`
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
  const gran = V.gran;
  let amb, nombre;
  if (!V.conDetalle) {
    amb = V.ddDet; nombre = delAl(amb.map((l) => l.d));
  } else if (V.provOk) {
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
  const itemK = campoParte(st);
  if (itemK && st.item != null) amb = amb.filter((l) => l[itemK] === st.item);
  const g = new Map();
  amb.forEach((l) => {
    const a = g.get(l.compra) || { compra: l.compra, fecha: l.d, doc: l.docLeg, prov: l.prov, lineas: 0, valor: 0, neto: 0, igv: 0, tipo: l.tipo, usd: l.usd };
    a.fecha = Math.min(a.fecha, l.d); a.lineas += 1; a.valor += l.v; a.neto += l.neto; a.igv += l.igv;
    g.set(l.compra, a);
  });
  const docs = [...g.values()].sort((a, b) => b.fecha - a.fecha || b.valor - a.valor || pyCmp(a.compra, b.compra));
  if (!docs.length) return { html: '<div class="vacio">Sin documentos.</div>', pie: '' };
  let sel;
  if (V.docOk && g.has(st.doc)) sel = st.doc;
  else if (gran === 'Por documento' && !V.provOk) sel = st.foco;
  else sel = null;
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
  const lin = sel ? amb.filter((l) => l.compra === sel) : [];
  const dSel = sel ? g.get(sel) : null;
  const colsL = [['prod', 'Producto', 'nm', null, '', 'minmax(80px,1fr)'], ['cant', 'Cantidad', 'r', (v) => (finito(v) ? num(v, 1) : ''), '', '78px'],
    ['punit', 'P. unit.', 'r', fS2, 'Precio unitario sin IGV', '84px'], ['valor', 'Valor sin IGV', 'r', fS2, '', '104px'],
    ['igv', 'IGV', '', null, 'Qué IGV paga el producto: 18 %, exonerado (verduras, pescados, frutas) o guía (todavía sin IGV: lo trae la factura)', '72px']];
  const filasL = lin.map((l) => ({ v: { prod: F.prods[l.prod], cant: l.cant, punit: l.punit, valor: l.neto, igv: igvDeLinea(Math.abs(l.neto), Math.abs(l.igv), l.tipo) },
    s: {}, tip: { prod: F.prods[l.prod] } }));
  const totL = { prod: `Total · ${lin.length} línea${lin.length === 1 ? '' : 's'}`, valor: `S/ ${num(suma(lin, (l) => l.neto), 2)}` };
  return { html: `<div class="det">${tabla('docs', colsD, filasD, totD, st, { cls: 'docs' })}</div>`,
  panel: dSel ? `<div class="pn-cab"><b title="${esc(F.provN[dSel.prov] || '')}">${esc(F.provN[dSel.prov] || F.provs[dSel.prov])}</b><button class="quita" data-acc="doc" data-v="">‹ Volver</button></div><p class="pn-sub">${esc(marca(dSel) + (dSel.doc || 'sin número'))} · ${dmy(dSel.fecha)} · ${esc(s2(dSel.neto))}</p><div class="pn-tabla">${tabla('lin', colsL, filasL, totL, st, { orden: { col: 'valor', dir: -1 }, cls: 'lin' })}</div>` : '',
  pie: `<b>${esc(nombre.replace(/<[^>]+>/g, ''))}</b> · ${num(docs.length, 0)} documentos · un clic en uno abre sus líneas al costado.`, colsD, filasD, colsL, filasL };
}

// ── Los filtros de la cabecera: menús, sin ocupar filas ─────────────────
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
// El filtro de familias es de la página: lo escribe Python (regla #770).
function menuFamilias(F, st) {
  const P = F.familias, abierto = st.menu === 'pag', el = new Set(P.elegidas), n = P.elegidas.length || P.todas.length;
  const txt = n === P.todas.length ? 'Todas las familias' : `Familias: ${n} de ${P.todas.length}`;
  return `<div class="ms"><button class="ms-b" data-acc="menu" data-v="pag" aria-expanded="${abierto}">${esc(txt)} <i>▾</i></button>`
    + (abierto ? `<div class="ms-l"><div class="ms-o">${P.todas.map(([f, v]) => `<label class="con-s"><input type="checkbox" data-acc="pagina" data-v="${esc(f)}"${el.has(f) || !el.size ? ' checked' : ''}><span>${esc(nomFam(f))}</span><small>${esc(s2(v).replace(/\.\d+$/, ''))}</small></label>`).join('')}</div><p class="mas">Vale para todas las vistas de Compras.</p></div>` : '') + '</div>';
}
const nomFam = (f) => { const x = String(f).toLowerCase(); return x.charAt(0).toUpperCase() + x.slice(1).replace(/ (con|sin|y|de) /g, (m) => m); };
// Agrupar, Partir por y Contra: en el nivel 3, al lado de los filtros (#792).
// Desde la #844 son «Nombre: valor ▾» sin caja, como en el boceto: cambian la
// forma de ver, no recortan. Lo que se ve es el rótulo; encima va un `<select>`
// transparente, que es el que abre la lista y recibe el teclado.
function menu(k, rot, aria, ops, val) {
  const txt = (ops.find(([v]) => v === val) || ops[0] || ['', ''])[1];
  return `<label class="men"><small>${rot}:</small><span>${esc(txt)}</span><i aria-hidden="true">▾</i>`
    + `<select data-sel="${k}" aria-label="${aria}">${ops.map(([v, t]) => `<option value="${esc(v)}"${v === val ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
}
function menusVista(F, V, st) {
  if (!V || V.vacio) return '';
  return menu('gran', 'Agrupar', 'Agrupar', GRANOS, st.gran)
    + (V.partidaGran ? menu('partir', 'Partir por', 'Partir por', (V.opsPartir || []).map((k) => [k, k]), st.partir) : '')
    + (F.C.length ? menu('contra', 'Contra', 'Contra qué comparar', [['ano', 'año pasado'], ['ant', 'período anterior'], ['no', 'sin comparar']], st.contra) : '');
}
// Nivel 2: qué se mira, y a la derecha «Cómo se calcula» (#792). Los íconos son
// los de la app (`iconos.js`, antepuesto; regla #821), con su nombre al cursor.
const ICO_VOLVER = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5"/></svg>';
const ampliar = (st, cual, rot) => {
  const on = st.amp === cual, n = on ? 'Volver (Esc)' : `Ampliar ${rot}`;
  return `<button class="ib amp-b" data-acc="amp" data-v="${cual}" aria-pressed="${on}" data-tip="${n}" data-tip-der aria-label="${n}">${on ? ICO_VOLVER : icono('ampliar')}</button>`;
};
function nivel2(F, V, st) {
  const zonas = [['graf', 'Gráfico'], ['tabla', 'Tabla'], ['docs', `Documentos${V && !V.vacio ? ` · ${num(new Set(V.dd.map((l) => l.compra)).size, 0)}` : ''}`]];
  const como = st.como ? `<div class="pop-como" role="dialog"><p>Lo comprado en el rango, sin IGV salvo que «Más filtros» diga otra cosa, con las notas de crédito ya restadas.</p><dl>`
    + '<dt>Compra</dt><dd>El valor comprado, contra el mismo tramo del año pasado o del período anterior. El período en curso se compara contra los mismos días.</dd>'
    + '<dt>Documentos</dt><dd>Comprobantes distintos en el rango, y lo comprado por documento.</dd>'
    + '<dt>Efecto del precio</dt><dd>Lo pagado menos lo que hubiera costado al precio habitual (la mediana de los 90 días anteriores), producto por producto, sin las compras para revisar.</dd>'
    + '<dt>Para revisar</dt><dd>Una compra de S/ 50 o más a 2,5 veces su habitual o a menos de 0,4, o con decimales en una unidad entera.</dd>'
    + '<dt>Documento</dt><dd>«Todos» es lo que suman los reportes de ingresos del Almacén, menos las notas de crédito. Sólo esta tarjeta.</dd></dl><p>Es un cálculo propio, no un estándar.</p></div>' : '';
  G.comoHtml = `<span class="como"><button class="link" data-acc="como" aria-expanded="${!!st.como}">Cómo se calcula</button>${como}</span>`;
  const movil = esMovil();
  return `<div class="n2"><div class="tabs" role="tablist">${zonas.map(([k, t]) => `<button role="tab" class="${k === st.zona ? 'on' : ''}" data-acc="zona" data-v="${k}" aria-selected="${k === st.zona}">${t}</button>`).join('')}</div>`
    + (movil || !V || V.vacio ? '' : capsula(F, V, st))
    + `<div class="n2-der">${movil ? G.comoHtml : ''}</div></div>`;
}
// El nivel 3, como el boceto (#844): los filtros («Más filtros» y la ficha de
// familias), a 24 px los menús de la vista y, al final, las acciones.
const TODOS = { sub: 'Todas las subfamilias', prov: 'Todos los proveedores', prod: 'Todos los productos' };
const VARIOS = { sub: 'subfamilias', prov: 'proveedores', prod: 'productos' };
function cabecera(F, V, st) {
  const activos = FILTROS.filter(([k]) => st[k].length).length + (st.docu !== 'Todos' ? 1 : 0) + (st.montos !== 'Sin IGV' ? 1 : 0);
  const local = !!F.familias?.en_panel;
  // #843: el filtro de familias de la vista es una ficha al lado de «Más filtros»
  // (`ficha_familias.js`). Familia y Subfamilia están siempre en «Más filtros»,
  // como campos; con filtro, además, la ficha, que abre su propio panel.
  const P = F.familias, conFicha = local && !!P.ficha, ffHay = conFicha && FichaFam.activo(P);
  const pend = conFicha ? (G.ffPend || FichaFam.iniciar(P)) : null;
  const ffO = conFicha ? { abierto: st.menu === 'ffam', pend: G.ffPend, envio: G.ffEnvio, q: st.q.ffsub, fmt: fmtK, campo: st.campo } : null;
  const disp = { fam: F.hayFam && V.famOps.length && !F.familias, sub: !local && F.haySub && V.subOps.length, prov: F.hayProv, prod: true };
  const dentro = FILTROS.filter(([k]) => disp[k] && k !== 'fam');
  const nFil = dentro.filter(([k]) => st[k].length).length;
  // Un campo de la pieza: plegado dice lo elegido; un clic abre su buscador y su lista.
  const nomDe = (k, o) => (k === 'prov' ? (F.provN[F.provs.indexOf(o)] || o) : o);
  const campoLocal = ([k, rot]) => FichaFam.campo(k, rot, !st[k].length ? TODOS[k] : st[k].length === 1 ? nomDe(k, st[k][0]) : `${st[k].length} ${VARIOS[k]}`, st.campo === k,
    () => `<input class="ms-q" data-k="${k}" placeholder="Buscar…" aria-label="Buscar ${rot.toLowerCase()}" value="${esc(st.q[k] || '')}" autocomplete="off"><div class="ms-o" data-k="${k}">${listaMenu(F, V, st, k)}</div>`
      + (st[k].length ? `<div class="ff-ats"><button class="ff-at" data-acc="limpiar" data-v="${k}">${TODOS[k]}</button></div>` : ''));
  const opciones = (rot, acc, ops, val) => `<div class="ff-c"><h4>${rot}</h4><div class="ops" role="group" aria-label="${rot}">${ops.map((k) => `<button class="${k === val ? 'on' : ''}" data-acc="${acc}" data-v="${k}" aria-pressed="${k === val}">${k}</button>`).join('')}</div></div>`;
  const famInt = disp.fam ? (() => { const s = st.fam, nom = (o) => F.famN[F.fams.indexOf(o)] || o, txt = !s.length ? 'Todas las familias' : s.length === 1 ? `Familia: ${nom(s[0])}` : `${s.length} familias`;
    return `<div class="ms"><button class="ms-b${s.length ? ' on' : ''}" data-acc="menu" data-v="fam" aria-expanded="${st.menu === 'fam'}">${esc(txt)} <i>▾</i></button>${st.menu === 'fam' ? `<div class="ms-l"><input class="ms-q" data-k="fam" placeholder="Buscar…" value="${esc(st.q.fam || '')}" autocomplete="off"><div class="ms-o" data-k="fam">${listaMenu(F, V, st, 'fam')}</div></div>` : ''}</div>`; })() : '';
  const nMas = nFil + (st.docu !== 'Todos' ? 1 : 0) + (st.montos !== 'Sin IGV' ? 1 : 0);
  const panelMas = st.menu === 'fil' ? '<div class="ms-l ancho" role="dialog" aria-label="Más filtros">'
    + (conFicha ? FichaFam.campo('ffam', 'Familia', FichaFam.rotuloFam(P, pend), st.campo === 'ffam', () => FichaFam.cuerpoFam(P, ffO))
      + FichaFam.campo('ffsub', 'Subfamilia', FichaFam.rotuloSub(P, pend), st.campo === 'ffsub', () => FichaFam.cuerpoSub(P, ffO)) : '')
    + dentro.map(campoLocal).join('')
    + opciones('Documento', 'docu', DOCUS, st.docu) + opciones('Montos', 'montos', MONTOS, st.montos)
    + (conFicha && G.ffPend && FichaFam.cambio(P, G.ffPend) ? '<div class="ff-pie"><span>Las familias se aplican al cerrar</span><button class="ff-ap" data-acc="ffam-aplicar">Aplicar</button></div>' : '')
    + '</div>' : '';
  const fil = (local ? '' : F.familias ? menuFamilias(F, st) : famInt)
    + `<div class="ms"><button class="ms-b${nMas ? ' on' : ''}" data-acc="menu" data-v="fil" aria-haspopup="dialog" aria-expanded="${st.menu === 'fil'}" title="${conFicha ? 'Familia, subfamilia, proveedor' : local ? 'Proveedor' : 'Subfamilia, proveedor'}, producto, documento y montos">Más filtros${nMas ? ` · ${nMas}` : ''} <i aria-hidden="true">▾</i></button>${panelMas}</div>`
    + (conFicha ? FichaFam.ficha(P, ffO) : '');
  const todos = activos + (ffHay ? 1 : 0), movil = esMovil();
  // Las acciones, al final y detrás de una raya: hacen algo una vez. En el
  // celular «Excel» sigue con su nombre y no hay «Ampliar».
  const acciones = movil ? '<button class="excel" data-acc="excel" title="Baja lo que se ve">Excel ↓</button>'
    : `<div class="acc">${G.comoHtml || ''}<button class="ib" data-acc="excel" data-tip="Descargar Excel" aria-label="Descargar Excel">${icono('bajar')}</button>`
      + (V && !V.vacio ? ampliar(st, 'izq', { graf: 'el gráfico', tabla: 'la tabla', docs: 'los documentos' }[st.zona]) : '') + '</div>';
  return `<div class="cab"><span class="lugar-fecha" aria-hidden="true"></span>`
    + `<button class="filtros-toggle" data-acc="panel-filtros" aria-expanded="${!!st.filtrosAbiertos}">Filtros${todos ? ` · ${todos} activo${todos === 1 ? '' : 's'}` : ''} <span aria-hidden="true">${st.filtrosAbiertos ? '▴' : '▾'}</span></button>`
    + `<div class="fils">${fil}</div><div class="mens">${menusVista(F, V, st)}</div><span class="esp"></span>${acciones}</div>`
    + `<div class="filtro-estado"><span>${esc(st.docu)} · ${esc(st.montos)}</span>`
    + (ffHay && !G.ffEnvio ? `<button data-acc="ffam-quitar" aria-label="Quitar el filtro de familias">${esc(FichaFam.rotulo(P))} ×</button>` : '')
    + FILTROS.filter(([k]) => st[k].length).map(([k, rot]) => `<button data-acc="limpiar" data-v="${k}" aria-label="Quitar filtro de ${rot}">${rot}: ${esc(st[k].length === 1 ? st[k][0] : st[k].length)} ×</button>`).join('')
    + (activos ? '<button data-acc="restablecer">Limpiar filtros</button>' : '') + '</div>';
}
// ── Los indicadores ──────────────────────────────────────────────────────
const fD0 = (v) => `${v > 0.5 ? '+' : v < -0.5 ? '−' : ''}S/ ${num(Math.abs(v), 0)}`;
const fS0 = (v) => `${v < -0.5 ? '−' : ''}S/ ${num(Math.abs(v), 0)}`;
function curvaKpi(xs) {
  if (!xs || xs.length < 2) return '';
  const a = Math.min(...xs), b = Math.max(...xs), r = b - a || 1;
  return `<svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><polyline points="${xs.map((x, i) => `${(i * 100 / (xs.length - 1)).toFixed(1)},${(31 - (x - a) / r * 28).toFixed(1)}`).join(' ')}"/></svg>`;
}
function datosKpi(F, V, st) {
  const tot = suma(V.tot, (x) => x), docs = new Set(V.dd.map((l) => l.compra)).size, provs = new Set(V.dd.map((l) => l.prov)).size;
  // La curva de doce meses mide los filtros de la página: con otro filtro no.
  const propios = FILTROS.some(([k]) => st[k].length) || st.docu !== 'Todos' || st.montos !== 'Sin IGV';
  const c = (i) => (propios ? null : F.meses.map((m) => m[i]));
  const nFam = !F.familias ? 'lo filtrado' : F.familias.ficha ? (FichaFam.rotulo(F.familias) || 'todas las familias')
    : `${F.familias.elegidas.length || F.familias.todas.length} de ${F.familias.todas.length} familias`;
  const vs = V.contraTot == null ? (st.contra === 'no' ? 'sin comparar' : 'sin datos para comparar')
    : V.contraTot > 0 ? (() => { const [t, cl] = fmtVariacion((tot - V.contraTot) / V.contraTot * 100); return `${esc(flecha(t))} contra ${esc(V.contraNom)}`; })() : `sin compras en ${esc(V.contraNom)}`;
  const E = V.efecto, neto = E.up + E.dn;
  // `corto`: lo que dice la cápsula plegada y la tira abierta (#842); `sub`, la fila del celular.
  const vsCorto = V.contraTot > 0 ? esc(flecha(fmtVariacion((tot - V.contraTot) / V.contraTot * 100)[0])) : '';
  return [
    { m: 'valor', rot: `Compra · ${nFam}`, nom: 'Compra', val: fS0(tot), sub: vs, corto: vsCorto, curva: c(1), tip: `Valor comprado en el rango, con las notas de crédito ya restadas.${V.contraTot > 0 ? ` Contra ${V.contraNom}.` : ''}` },
    { m: 'docs', rot: 'Documentos', nom: 'Documentos', val: num(docs, 0), sub: `${esc(fS0(docs ? tot / docs : 0))} por documento · ${num(provs, 0)} proveedores`, corto: `${esc(fS0(docs ? tot / docs : 0))} c/u`, curva: c(2), tip: `Comprobantes distintos en el rango, de ${num(provs, 0)} proveedores.` },
    { m: 'precio', rot: 'Efecto del precio', nom: 'Efecto del precio', val: fD0(neto), sub: `${num(E.nUp, 0)} subieron ${esc(fD0(E.up))} · ${num(E.nDn, 0)} bajaron ${esc(fD0(E.dn))}`, corto: `${num(E.nUp, 0)} subieron`, curva: c(3), tip: `Lo pagado menos lo que hubiera costado al precio habitual (la mediana de los 90 días anteriores), producto por producto, sin las compras para revisar. ${num(E.nUp, 0)} subieron ${fD0(E.up)} y ${num(E.nDn, 0)} bajaron ${fD0(E.dn)}.`, cls: neto > 0.5 ? 'sube' : neto < -0.5 ? 'baja' : '' },
    { m: 'revisar', rot: 'Para revisar', nom: 'Para revisar', val: `${num(V.revProd, 0)} producto${V.revProd === 1 ? '' : 's'}`, sub: `${num(V.revLin, 0)} compra${V.revLin === 1 ? '' : 's'} por ${esc(fS0(V.revVal))} · no entran en el precio`, corto: `${num(V.revLin, 0)} compra${V.revLin === 1 ? '' : 's'}`, curva: c(4), tip: `Una compra de S/ 50 o más a 2,5 veces su precio habitual o a menos de 0,4, o con decimales en una unidad que se cuenta entera. ${num(V.revLin, 0)} compras por ${fS0(V.revVal)}: no entran en el precio.`, cls: V.revProd ? 'aviso' : '', n: V.revProd },
  ];
}
const botonKpi = (st, k, sub) => `<button class="kpi${st.med === k.m ? ' on' : ''}" data-acc="medida" data-v="${k.m}" aria-pressed="${st.med === k.m}" title="${esc(k.tip)}">${curvaKpi(k.curva)}<span class="r">${esc(k.rot)}</span><span class="v ${k.cls || ''}">${esc(k.val)}</span><span class="d">${sub}</span></button>`;
// La fila de siempre: en el celular, donde no hay renglón libre para la cápsula.
function indicadores(F, V, st) {
  return `<div class="kpis">${datosKpi(F, V, st).map((k) => botonKpi(st, k, k.sub)).join('')}</div>`;
}
// #842: en escritorio los indicadores van plegados en el renglón de las pestañas,
// que estaba casi vacío. Plegada, la cápsula dice qué mide el gráfico y con qué
// se compara, y avisa lo que hay para revisar. Abierta, la tira ocupa ese mismo
// hueco hacia la izquierda: no tapa las pestañas ni corre nada (#465).
function capsula(F, V, st) {
  const ks = datosKpi(F, V, st), k = ks.find((x) => x.m === st.med) || ks[0], rev = ks[3].n;
  if (!st.kAb) {
    return `<div class="kz"><button class="kcap" data-acc="kpis" aria-expanded="false" title="Ver los cuatro indicadores">`
      + `<span class="r">${esc(k.nom)}</span><span class="v ${k.cls || ''}">${esc(k.val)}</span>${k.corto ? `<span class="c">${k.corto}</span>` : ''}`
      + `<span class="mas">${rev && k.m !== 'revisar' ? `<i class="pto" title="${num(rev, 0)} para revisar">${num(rev, 0)}</i>` : ''}3 más ‹</span></button></div>`;
  }
  return `<div class="kz abierta"><div class="ktira" role="group" aria-label="Indicadores">${ks.map((x) => botonKpi(st, x, x.corto)).join('')}`
    + '<button class="kcerrar" data-acc="kpis" aria-expanded="true" title="Plegar (Esc)" aria-label="Plegar los indicadores">✕</button></div></div>';
}
// ── La lista del costado ─────────────────────────────────────────────────
const campoParte = (st) => ({ [FAM]: 'fam', [SUB]: 'sub', [PROV]: 'prov' }[st.partir] || null);
function nombreParte(F, st, x) { return st.partir === FAM ? F.famN[x] : st.partir === SUB ? F.subN[x] : F.provC[x]; }
function panelLista(F, V, st) {
  const campo = campoParte(st), foco = st.foco != null && V.ix.has(st.foco) ? st.foco : null;
  const base = foco ? V.dd.filter((l) => l.clave === foco) : V.dd;
  const tit = foco ? esc((V.gran === 'Día' ? V.hov[V.ix.get(foco)] : (V.rotDe.get(foco) || [foco, foco])[1]).replace(/<[^>]+>/g, '')) : ({ [FAM]: 'Por familia', [SUB]: 'Por subfamilia', [PROV]: 'Por proveedor', [PRECIO]: 'Contra el precio habitual' }[st.partir]);
  let filas = '', ficha = '';
  if (campo) {
    const m = new Map();
    base.forEach((l) => { const a = m.get(l[campo]) || { k: l[campo], ls: [], v: 0 }; a.ls.push(l); a.v += l.v; m.set(l[campo], a); });
    // Contra lo de un año o un período antes, en la misma ventana.
    const [a0, b0] = foco ? limites(foco, V.gran).map((x, i) => (i ? Math.min(x, F.R1) : Math.max(x, F.R0))) : [F.R0, F.R1];
    const [ca, cb] = V.atras(a0, b0), hayC = st.contra !== 'no' && V.enBase(ca) && V.gran !== 'Por documento';
    const cPor = new Map();
    if (hayC) F.C.forEach((l) => { if (l.d >= ca && l.d <= cb) cPor.set(l[campo], (cPor.get(l[campo]) || 0) + l.neto + (V.conIgv ? l.igv : 0)); });
    const total = base.reduce((s, l) => s + l.v, 0) || 1, medir = (ls) => (st.med === 'docs' ? new Set(ls.map((l) => l.compra)).size : st.med === 'revisar' ? suma(ls.filter((l) => l.fl), (l) => l.v) : st.med === 'precio' ? suma(ls.filter((l) => !l.fl && l.cant > 0 && finito(l.refT)), (l) => l.neto - l.refT * l.cant) : suma(ls, (l) => l.v));
    const ordenes = [...m.values()].map((x) => ({ ...x, val: medir(x.ls) })).filter((x) => st.med !== 'revisar' || x.val > 0).sort((p, q) => (st.med === 'precio' ? Math.abs(q.val) - Math.abs(p.val) : q.val - p.val));
    const tono = new Map(V.partes.map((p, q) => [p[0], colorParte(V, q)]));
    filas = ordenes.map((x) => {
      const nom = nombreParte(F, st, x.k), pct = Math.round(x.v / total * 100), c0 = cPor.get(x.k), va = hayC && c0 > 0 ? fmtVariacion((x.v - c0) / c0 * 100) : null;
      const val = st.med === 'docs' ? num(x.val, 0) : st.med === 'precio' ? fD0(x.val) : fmtK(x.val);
      const cl = st.med === 'precio' ? (x.val > 0.5 ? 'sube' : x.val < -0.5 ? 'baja' : '') : '';
      return `<button class="fi${st.item === x.k ? ' on' : ''}" data-acc="item" data-v="${x.k}" title="${esc(nom)}"><span class="n"><i style="background:${tono.get(nom) || 'var(--cp-otro)'}"></i>${esc(nom)}</span><b class="${cl}">${esc(val)}</b><small>${pct} %${va ? ` · ${esc(flecha(va[0]))}` : ''}</small></button>`;
    }).join('');
    const it = st.item != null ? m.get(st.item) : null;
    if (it) {
      const prods = new Map();
      it.ls.forEach((l) => prods.set(l.prod, (prods.get(l.prod) || 0) + l.v));
      const top = [...prods.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
      const ef = suma(it.ls.filter((l) => !l.fl && l.cant > 0 && finito(l.refT)), (l) => l.neto - l.refT * l.cant);
      ficha = `<div class="pn-ficha"><div class="pn-cab"><b title="${esc(nombreParte(F, st, st.item))}">${esc(nombreParte(F, st, st.item))}</b><button class="quita" data-acc="item" data-v="${st.item}">Soltar</button></div>`
        + `<div class="pr"><span>Pesa en lo elegido</span><b>${Math.round(it.v / total * 100)} %</b></div><div class="pr"><span>Efecto del precio</span><b class="${ef > 0.5 ? 'sube' : ef < -0.5 ? 'baja' : ''}">${esc(fD0(ef))}</b></div>`
        + top.map(([p, v]) => `<div class="pr"><span title="${esc(F.prods[p])}">${esc(F.prods[p])}</span><b>${esc(fmtK(v))}</b></div>`).join('')
        + `<button class="ir" data-acc="zona" data-v="docs">Ver sus documentos →</button></div>`;
    }
  } else {
    filas = V.partes.map((p, q) => { const v = foco ? p[2][V.ix.get(foco)] : suma(p[2], (x) => x), t = foco ? V.tot[V.ix.get(foco)] : suma(V.tot, (x) => x); return `<div class="fi"><span class="n"><i style="background:${colorParte(V, q)}"></i>${esc(p[0])}</span><b>${esc(fmtK(v))}</b><small>${Math.round((t ? v / t : 0) * 100)} %</small></div>`; }).join('');
  }
  let fuera = '';
  if (F.familias && st.item == null) {
    const P = F.familias, el = new Set(P.elegidas), fx = P.todas.filter(([f]) => el.size && !el.has(f)), v = suma(fx, (x) => x[1]);
    const sumar = P.ficha ? '<button class="quita" data-acc="ffam-todas">Sumarlas</button>' : P.en_panel ? '' : '<button class="quita" data-acc="pagina-todas">Sumarlas</button>';
    if (fx.length && Math.abs(v) >= 0.5) fuera = `<div class="fuera"><span>Fuera de esta cuenta: ${esc(fS0(v))} de ${esc(fx.slice(0, 2).map(([f]) => nomFam(f)).join(', '))}${fx.length > 2 ? '…' : ''}.</span>${sumar}</div>`;
  }
  return `<div class="pn-cab"><b>${tit}</b>${ampliar(st, 'panel', 'la lista')}</div><div class="lista">${filas || '<p class="mas">Nada que mostrar.</p>'}</div>${ficha}${fuera}`;
}
// ── Dibujar ──────────────────────────────────────────────────────────────
function pintar() {
  const raiz = G.raiz, F = G.F, st = G.st;
  if (!raiz || !F) return;
  // Cambiar el grano, un filtro o Documento suelta el foco (el `_ctx` de antes).
  const ctx = JSON.stringify([st.gran, st.fam, st.sub, st.prov, st.prod, st.docu]);
  if (st.ctx !== ctx) { st.ctx = ctx; st.foco = null; st.doc = null; st.lectura = null; }
  const V = calcular(F, st);
  G.V = V;
  if (!st.menu) st.campo = null;
  raiz.dataset.filtrosAbiertos = String(!!st.filtrosAbiertos);
  raiz.classList.toggle('amp', !!st.amp);
  let html = nivel2(F, V, st) + cabecera(F, V, st);
  if (V.vacio) {
    raiz.innerHTML = html + `<div class="vacio grande"><b>${esc(V.titulo)}</b> — sin compras que mostrar. Ampliá el rango de fechas o soltá algún filtro de la tarjeta.</div>`;
    return;
  }
  if (esMovil()) html += indicadores(F, V, st);
  const nomFoco = st.foco != null && V.ix.has(st.foco) ? (V.gran === 'Día' ? V.hov[V.ix.get(st.foco)] : (V.rotDe.get(st.foco) || [st.foco, st.foco])[1]).replace(/<[^>]+>/g, '') : null;
  const quitar = nomFoco ? `<button class="quita" data-acc="quita-foco">Ver todo el rango ✕</button>` : '';
  let izq, panel = panelLista(F, V, st);
  st.modo = st.zona === 'docs' ? 'Detalle' : st.modo === 'Detalle' ? 'Resumen Total' : st.modo;
  G.zona = null;
  if (st.zona === 'graf') {
    const NOM = { valor: 'Compra', docs: 'Documentos', precio: 'Efecto del precio', revisar: 'Compras para revisar' };
    const SUBT = { valor: V.sufijo.replace(/^ · /, ''), docs: 'comprobantes distintos', precio: 'lo que subió arriba, lo que bajó abajo', revisar: 'valor de las líneas marcadas' };
    const hayPar = V.claves.some((k) => { const [a, b] = cobertura(k, V.gran, V.rango); return V.gran !== 'Por documento' && V.gran !== 'Día' && a < b; });
    izq = `<div class="tit"><span class="t">${NOM[st.med]} ${esc(AGRUPADO[V.gran] === 'documento' ? 'por documento' : `por ${AGRUPADO[V.gran]}`)}<small> · ${esc(SUBT[st.med])}${hayPar ? ' · * período incompleto' : ''}</small></span>${quitar}<span class="esp"></span>${V.ghost.some((x) => x != null) && st.med === 'valor' ? `<span class="ley"><i></i>${st.contra === 'ano' ? 'año pasado' : 'período anterior'}</span>` : ''}${st.amp === 'izq' ? ampliar(st, 'izq', 'el gráfico') : ''}</div>`
      + `<div class="graf" data-graf="1"><div class="tip" hidden></div></div>`;
    if (esMovil()) {
      izq += st.lectura != null && st.lectura < V.n ? `<div class="lectura" role="region" aria-label="Detalle del período"><button class="lectura-cerrar" data-acc="cerrar-lectura" aria-label="Cerrar detalle">×</button><div>${tip(F, V, st, st.lectura)}</div><button class="ver-documentos" data-acc="ver-barra" data-v="${st.lectura}">Ver documentos de este período</button></div>` : '<p class="ayuda-tocar">Toca una barra para ver su desglose.</p>';
    }
    if (V.n === 1) izq += '<p class="aviso1">Sólo hay compras en un período dentro del rango: ampliá el rango para ver la evolución.</p>';
    G.zona = resumenTotal(F, V, st);
  } else if (st.zona === 'tabla') {
    const z = st.modo === 'Resumen del Período' ? resumenProveedores(F, V, st) : resumenTotal(F, V, st);
    G.zona = z;
    izq = `<div class="tit"><div class="seg chico">${[['Resumen Total', 'Por período'], ['Resumen del Período', 'Por proveedor']].map(([k, t]) => `<button class="${k === st.modo ? 'on' : ''}" data-acc="modo" data-v="${k}">${t}</button>`).join('')}</div><span class="cap">${z.pie}</span>${st.amp === 'izq' ? ampliar(st, 'izq', 'la tabla') : ''}</div><div class="zona">${z.html}</div>`;
  } else {
    const z = detalle(F, V, st);
    G.zona = z;
    izq = `<div class="tit"><span class="cap">${z.pie}</span>${quitar}${st.amp === 'izq' ? ampliar(st, 'izq', 'los documentos') : ''}</div><div class="zona">${z.html}</div>`;
    if (z.panel) panel = z.panel;
  }
  html += `<div class="cuerpo" data-amp="${st.amp || ''}"><div class="izq">${izq}</div><aside class="panel" aria-label="Lo que hay adentro">${panel}</aside></div>`;
  const listas = [...raiz.querySelectorAll('.tl')].map((e) => e.scrollTop);
  // Marcar una casilla redibuja la pieza: el menú abierto conserva por dónde
  // iba su lista y la casilla que tenía el foco (el teclado sigue ahí).
  const MENUS = '.ms-l, .ms-o, .ff-l, .ff-o', menus = [...raiz.querySelectorAll(MENUS)].map((e) => e.scrollTop);
  const q = raiz.querySelector('.ms-q:focus, .ff-q:focus'), cas = raiz.querySelector('input[type="checkbox"]:focus');
  const casilla = cas ? [cas.dataset.acc, cas.dataset.k || '', cas.dataset.v] : null;
  raiz.innerHTML = html;
  [...raiz.querySelectorAll('.tl')].forEach((e, i) => { if (listas[i]) e.scrollTop = listas[i]; });
  const menus2 = [...raiz.querySelectorAll(MENUS)];
  if (menus2.length === menus.length) menus2.forEach((e, i) => { if (menus[i]) e.scrollTop = menus[i]; });
  if (q) { const n = raiz.querySelector(`.ms-q[data-k="${q.dataset.k}"], .ff-q[data-k="${q.dataset.k}"]`); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }
  else if (casilla) { const n = [...raiz.querySelectorAll(`input[type="checkbox"][data-acc="${casilla[0]}"]`)].find((e) => (e.dataset.k || '') === casilla[1] && e.dataset.v === casilla[2]); if (n) n.focus(); }
  // La fecha es un botón de Python en la misma página: la cabecera le deja su ancho.
  ponerFecha(raiz);
  const cg = raiz.querySelector('[data-graf]');
  if (cg) {
    const W = cg.clientWidth || 800, H = esMovil() ? Math.max(230, Math.min(320, Math.round(window.innerHeight * 0.38))) : Math.max(150, cg.clientHeight || 300);
    const gr = grafico(F, V, st, W, H);
    G.X = gr.X; G.W = W;
    cg.insertAdjacentHTML('afterbegin', gr.svg);
  }
}

function pintarTip(i) {
  if (esMovil()) return;
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
  if (z.colsD) hojas = [hoja('Documentos', z.colsD, z.filasD), ...(z.filasL.length ? [hoja('Líneas', z.colsL, z.filasL)] : [])];
  else if (z.cols) hojas = [hoja(st.modo, z.cols, z.filas)];
  else return;
  bajar(`compras_por_periodo_${archivo(st.modo)}_${iso(G.F.R0)}_${iso(G.F.R1)}.xlsx`, libro(hojas));
}

// ── Los clics ────────────────────────────────────────────────────────────
function ponerFecha(raiz) {
  const fb = document.querySelector('.st-key-cp_sem_fecha'), lg = raiz.querySelector('.lugar-fecha');
  if (!fb) return;
  const ver = !!(lg && lg.offsetWidth);
  if (fb.style.visibility !== (ver ? '' : 'hidden')) fb.style.visibility = ver ? '' : 'hidden';
  if (!ver || !fb.offsetWidth) return;
  const w = `${fb.offsetWidth + 8}px`;
  if (raiz.style.getPropertyValue('--cp-fecha') !== w) raiz.style.setProperty('--cp-fecha', w);
  const pa = fb.offsetParent;
  if (!pa) return;
  const a = lg.getBoundingClientRect(), b = pa.getBoundingClientRect();
  const x = `${Math.round(a.left - b.left)}px`, y = `${Math.round(a.top - b.top + (lg.offsetHeight > 2 ? (a.height - fb.offsetHeight) / 2 : -fb.offsetHeight / 2))}px`;
  if (fb.style.left !== x) fb.style.left = x;
  if (fb.style.top !== y) fb.style.top = y;
}
// #843: lo que la ficha de familias le pide a Python. Mientras no vuelve, la
// ficha dice lo pedido, apagada; si Python no lo aplica, a los 20 s se suelta.
function enviarFf(v) {
  const P = G.F && G.F.familias;
  if (!P || !P.ficha || !FichaFam.distinto(P, v)) { pintar(); return; }
  G.ffEnvio = v;
  clearTimeout(G.ffReloj);
  G.ffReloj = setTimeout(() => { G.ffEnvio = null; pintar(); }, 20000);
  G.enviar?.('familias', v);
  pintar();
}
// Al cerrarse el panel, por el camino que sea, lo marcado se aplica UNA vez.
function soltarFf() {
  const P = G.F && G.F.familias;
  // Los dos menús donde se marcan familias: el panel de la ficha y «Más filtros».
  if (!G.ffPend || !G.st || G.st.menu === 'ffam' || G.st.menu === 'fil') return;
  const v = P && P.ficha ? FichaFam.cambio(P, G.ffPend) : null;
  G.ffPend = null;
  if (v) enviarFf(v);
}
function accion(acc, val, el) {
  const st = G.st, V = G.V;
  if (acc === 'barra' && esMovil()) { st.lectura = +val; pintar(); return; }
  const verDocumentos = acc === 'ver-barra';
  if (verDocumentos) { acc = 'barra'; st.lectura = null; }
  const P = G.F.familias;
  if (!['menu', 'filtro', 'docu', 'montos', 'limpiar', 'ffam-menu', 'ffam-fam', 'ffam-sub', 'ffam-sublimpiar', 'campo'].includes(acc)) st.menu = null;
  if (acc !== 'como') st.como = false;
  if (acc === 'como') st.como = !st.como;
  else if (acc === 'amp') st.amp = st.amp === val ? null : val;
  else if (acc === 'panel-filtros') st.filtrosAbiertos = !st.filtrosAbiertos;
  else if (acc === 'cerrar-lectura') st.lectura = null;
  else if (acc === 'restablecer') { FILTROS.forEach(([k]) => { st[k] = []; }); st.docu = 'Todos'; st.montos = 'Sin IGV'; }
  else if (acc === 'gran') st.gran = val;
  else if (acc === 'menu') { st.menu = st.menu === val ? null : val; }
  else if (acc === 'filtro') {
    const k = el.dataset.k, xs = st[k];
    st[k] = el.checked ? [...xs, val] : xs.filter((x) => x !== val);
  } else if (acc === 'limpiar') { st[val] = []; }
  else if (acc === 'medida') { st.med = val; st.item = null; }
  else if (acc === 'kpis') st.kAb = !st.kAb;
  else if (acc === 'zona') { st.zona = val; if (val === 'tabla' && st.modo === 'Detalle') st.modo = 'Resumen Total'; }
  else if (acc === 'quita-foco') { st.foco = null; st.doc = null; }
  else if (acc === 'item') { const k = Number(val), igual = st.item === k; st.item = igual ? null : k; const nom = igual ? null : nombreParte(G.F, st, k); st.res[st.partir] = nom != null && V.opsRes.includes(nom) ? nom : null; }
  else if (acc === 'pagina') { const P = G.F.familias, el = P.elegidas.length ? P.elegidas : P.todas.map((x) => x[0]); P.elegidas = el.includes(val) ? el.filter((x) => x !== val) : [...el, val]; G.pagina = P.elegidas.slice(); st.menu = 'pag'; }
  else if (acc === 'pagina-todas') { G.pagina = G.F.familias.todas.map((x) => x[0]); G.enviar?.('familias', G.pagina); return; }
  // #843: la ficha de familias. Las casillas marcan `G.ffPend` y se aplican al
  // cerrar el panel (`soltarFf`); la ✕ y los atajos se piden en el acto.
  else if (acc === 'campo') st.campo = st.campo === val ? null : val;
  else if (acc === 'ffam-menu') { st.menu = st.menu === 'ffam' ? null : 'ffam'; if (st.menu && !G.ffPend) G.ffPend = FichaFam.iniciar(P); }
  else if (acc === 'ffam-fam') G.ffPend = FichaFam.alternarFam(P, G.ffPend || FichaFam.iniciar(P), val);
  else if (acc === 'ffam-sub') G.ffPend = FichaFam.alternarSub(P, G.ffPend || FichaFam.iniciar(P), val);
  else if (acc === 'ffam-sublimpiar') G.ffPend = { fam: (G.ffPend || FichaFam.iniciar(P)).fam, sub: [] };
  else if (acc === 'ffam-aplicar') { /* El panel ya se cerró: lo marcado lo manda `soltarFf`. */ }
  else if (acc === 'ffam-quitar' || acc === 'ffam-todas') { G.ffPend = null; enviarFf(FichaFam.sinFiltro()); return; }
  else if (acc === 'ffam-entrada') { G.ffPend = null; enviarFf(FichaFam.deEntrada(P)); return; }
  else if (acc === 'docu') st.docu = val;
  else if (acc === 'montos') st.montos = val;
  else if (acc === 'modo') st.modo = val;
  else if (acc === 'barra') {
    // Elegir una barra no salta: la lista del costado pasa a ser la de esa barra.
    const k = V.claves[+val];
    st.provDet = null; st.doc = null; st.foco = st.foco === k && !verDocumentos ? null : k;
    if (verDocumentos) { st.zona = 'docs'; st.modo = 'Detalle'; }
  } else if (acc === 'fila-per') { st.provDet = null; st.doc = null; st.foco = val; st.zona = 'docs'; st.modo = 'Detalle'; }
  else if (acc === 'prov') { st.provDet = val; st.foco = null; st.doc = null; st.zona = 'docs'; st.modo = 'Detalle'; }
  else if (acc === 'doc') {
    st.doc = val || null;
  } else if (acc === 'ordenar') {
    const [id, col] = val.split('|'), o = st.orden[id];
    st.orden[id] = !o || o.col !== col ? { col, dir: -1 } : o.dir < 0 ? { col, dir: 1 } : null;
  } else if (acc === 'excel') { excel(); return; }
  else return;
  pintar();
  if (acc === 'panel-filtros') G.raiz.querySelector('.filtros-toggle')?.focus();
  if (verDocumentos) G.raiz.querySelector('.cuerpo')?.scrollIntoView({ block: 'start' });
}
function enlazar(raiz) {
  raiz.addEventListener('keydown', (ev) => {
    if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches('.hit')) { ev.preventDefault(); ev.target.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
  });
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.disabled) return;
    if ((b.dataset.acc === 'filtro' || b.dataset.acc === 'pagina') && b.tagName !== 'INPUT') return;
    accion(b.dataset.acc, b.dataset.v, b);
    soltarFf();
    // Un campo que se abre al pie de su panel queda a la vista sin deslizar.
    if (b.dataset.acc === 'campo') raiz.querySelector('.ff-cl')?.scrollIntoView({ block: 'nearest' });
  });
  raiz.addEventListener('input', (ev) => {
    const q = ev.target.closest('.ms-q, .ff-q');
    if (!q) return;
    const k = q.dataset.k;
    G.st.q[k] = q.value;
    const o = raiz.querySelector(`.ms-o[data-k="${k}"], .ff-o[data-k="${k}"]`);
    if (!o) return;
    o.innerHTML = k === 'ffsub' ? FichaFam.listaSub(G.F.familias, G.ffPend || FichaFam.iniciar(G.F.familias), q.value) : listaMenu(G.F, G.V, G.st, k);
  });
  raiz.addEventListener('change', (ev) => {
    const k = ev.target.dataset && ev.target.dataset.sel;
    if (!k) return;
    G.st[k] = ev.target.value; G.st.menu = null;
    if (k === 'partir') { G.st.item = null; G.st.res[G.st.partir] = null; }
    pintar();
    soltarFf();
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
    const avisar = () => { if (G.pagina) { const v = G.pagina; G.pagina = null; G.enviar?.('familias', v); } };
    document.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Escape' || !G.st || !G.raiz || !G.raiz.isConnected) return;
      if (G.st.menu) { G.st.menu = null; pintar(); avisar(); soltarFf(); } else if (G.st.como) { G.st.como = false; pintar(); } else if (G.st.kAb) { G.st.kAb = false; pintar(); } else if (G.st.amp) { G.st.amp = null; pintar(); }
    });
    document.addEventListener('pointerdown', (ev) => {
      if (!G.st || !G.st.menu) return;
      // Un control de la pieza lo cierra en su propio clic (redibujar acá
      // borraría el botón antes de que el clic llegue).
      if (ev.composedPath().some((n) => n.classList && (n.classList.contains('ms') || n.classList.contains('ff') || (n.dataset && n.dataset.acc)))) return;
      G.st.menu = null;
      pintar();
      avisar();
      soltarFf();
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
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.lineas) return;
  G.enviar = setTriggerValue;
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
  // #843: llegó lo que la ficha de familias le pidió a Python; deja de esperar.
  G.ffEnvio = null; G.ffPend = null; clearTimeout(G.ffReloj);
  if (G.st.menu === 'ffam') G.st.menu = null;
  pintar();
}
