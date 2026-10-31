// Ventas › «Análisis de platos» › Ranking (reglas #699 y #767).
//
// La monta graficos/ventas_platos.py::_pieza_ranking con st.components.v2
// (sin iframe, estilos en un shadow root), con `ventas_platos_cromo.js`
// antepuesto. Una fila de controles, cuatro indicadores y UNA zona por pestaña
// —Tabla o Puestos— con la ficha del plato al costado. El corte y los períodos
// cargan datos: vuelven a Python por el trigger `cromo`, igual que el paso a la
// Ingeniería de menú. Vuelven también `foco` (el plato elegido: su evolución en
// todo el corte se carga allá), `hora` y `carta`. Lo demás se resuelve acá.
//
// LAS CUENTAS SON LAS DE ventas_platos.py: `puestos` (empates con el puesto
// más alto, sin venta no hay puesto), `movimiento` (verde o rojo desde
// `salto` puestos) y `var_por_dia` (por día CON venta). El test busca las
// fórmulas escritas igual.
//
// Python manda en `data`: `periodos` ([{etq, dias}], del más viejo al más
// nuevo), `platos` ([nombre, grupo, subgrupo, [venta], [unidades], [costo],
// [neto], código]), `foco`, `evolucion` ({nombre, corte, serie: [etiqueta,
// venta/día, unidades/día, elegido]}), `umbrales` ([45, 70]), `salto`,
// `tope`, `max_elegidos` y `cromo`.

const PALETA = ['#6c5ce7', '#0e9fb8', '#e85ba8', '#d97706', '#16a34a', '#9385ec', '#c2410c', '#4938b8', '#0f766e', '#be185d'];
const TOPES = [['10', 'Top 10'], ['15', 'Top 15'], ['20', 'Top 20'], ['todos', 'Todos'], ['elegidos', 'Elegidos']];
const esc = escPl;
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const soles = (v) => `S/ ${Math.round(v).toLocaleString('en-US')}`;
const corto = (v) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(Math.round(v)));
const num = (v) => Number(v || 0).toLocaleString('en-US', { maximumFractionDigits: 1 });
const recorta = (s, n) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
function signo(x) { return `${x >= 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(0)} %`; }

// ── Las cuentas de ventas_platos.py ──────────────────────────────────────
function puestos(valores) {
  // Map nombre → puesto: 1 el que más; empatados, el puesto más alto.
  const v = [...valores].filter(([, x]) => x > 0).sort((a, b) => b[1] - a[1]);
  const out = new Map();
  v.forEach(([n, x], i) => { out.set(n, i > 0 && x === v[i - 1][1] ? out.get(v[i - 1][0]) : i + 1); });
  return out;
}
function movimiento(d, p0, p1) {
  if (!p0 && p1) return ['entra', 'entra'];
  if (p0 && !p1) return ['sale', 'sale'];
  if (!p0 && !p1) return ['—', 'igual'];
  const dd = p0 - p1;
  if (dd > 0) return [`▲ ${dd}`, dd >= d.salto ? 'sube' : 'igual'];
  if (dd < 0) return [`▼ ${-dd}`, -dd >= d.salto ? 'baja' : 'igual'];
  return ['=', 'igual'];
}
function varPorDia(v0, d0, v1, d1) {
  const a = d0 ? v0 / d0 : 0, b = d1 ? v1 / d1 : 0;
  return a ? (b - a) / a : null;
}
const pctCosto = (costo, neto) => (costo > 0 && neto > 0.5 ? costo / neto * 100 : null);
function nivel(d, p) { return p == null ? '' : p > d.umbrales[1] ? 'rojo' : p > d.umbrales[0] ? 'ambar' : ''; }

// ── Lo que entra según lo elegido ────────────────────────────────────────
function calcular(d, st) {
  const P = d.periodos, n = P.length, pri = 0, ult = n - 1, m = st.medida === 'cant' ? 4 : 3;
  const enAmb = d.platos.filter((p) => !st.ambito || (st.ambito[0] === 'g' ? p[1] === st.ambito[1] : p[2] === st.ambito[1]));
  const pue = P.map((_, i) => puestos(enAmb.map((p) => [p[0], p[m][i]])));
  const orden = enAmb.slice().sort((a, b) => (pue[ult].get(a[0]) || 1e6) - (pue[ult].get(b[0]) || 1e6) || b[m][pri] - a[m][pri]);
  let filas;
  if (st.mostrar === 'elegidos') filas = orden.filter((p) => st.elegidos_p.includes(p[0]));
  else if (st.mostrar === 'todos') filas = orden.filter((p) => P.some((_, i) => pue[i].get(p[0])));
  else filas = orden.filter((p) => (pue[ult].get(p[0]) || 1e6) <= +st.mostrar);
  const enGraf = st.mostrar === 'elegidos' ? filas : filas.filter((p) => (pue[ult].get(p[0]) || 1e6) <= d.tope);
  return { P, n, pri, ult, m, enAmb, pue, filas, enGraf };
}

// ── Indicadores ──────────────────────────────────────────────────────────
function htmlKpis(d, st, c) {
  const { P, pri, ult, m, enAmb, pue } = c;
  const tot = (i) => enAmb.reduce((s, p) => s + p[m][i], 0);
  const g = varPorDia(tot(pri), P[pri].dias, tot(ult), P[ult].dias);
  const nombres = enAmb.map((p) => p[0]);
  const dif = nombres.filter((x) => pue[pri].get(x) && pue[ult].get(x)).map((x) => [x, pue[pri].get(x) - pue[ult].get(x)]);
  const sube = dif.filter(([x]) => pue[ult].get(x) <= d.tope).reduce((a, b) => (b[1] > (a ? a[1] : 0) ? b : a), null);
  const baja = dif.filter(([x]) => pue[pri].get(x) <= d.tope).reduce((a, b) => (b[1] < (a ? a[1] : 0) ? b : a), null);
  const raros = enAmb.filter((p) => (pue[ult].get(p[0]) || 1e6) <= d.tope && pctCosto(p[5][ult], p[6][ult]) > d.umbrales[1]);
  const amb = st.ambito ? st.ambito[1] : 'toda la carta';
  const k = (rot, val, sub, cls = '', tip = '', id = '') => `<${id ? 'button type="button"' : 'div'} class="vp-kpi${id ? ' clic' : ''}" title="${esc(tip || rot)}"${id ? ` data-acc="foco" data-id="${esc(id)}"` : ''}><span class="vp-kpi-rot">${esc(rot)}</span>
    <span class="vp-kpi-lin"><span class="vp-kpi-val ${cls}">${val}</span><span class="vp-kpi-sub">${sub}</span></span></${id ? 'button' : 'div'}>`;
  const compara = P.length > 1;
  return [
    compara ? k(`${amb.charAt(0).toUpperCase() + amb.slice(1)} por día`, g == null ? '—' : signo(g),
      `${st.medida === 'cant' ? num(tot(pri) / P[pri].dias) : soles(tot(pri) / P[pri].dias)} → ${st.medida === 'cant' ? num(tot(ult) / P[ult].dias) : soles(tot(ult) / P[ult].dias)}`,
      g == null ? '' : g >= 0 ? 'verde' : 'rojo', `Por día con venta, de ${P[pri].etq} a ${P[ult].etq}: la vara con que se mide cada plato`)
      : k(`Platos con venta · ${P[ult].etq}`, String(pue[ult].size), `en ${esc(amb)}`),
    compara ? k('Sube más', sube ? esc(recorta(sube[0], 22)) : '—', sube ? `▲ ${sube[1]} puestos` : '', 'verde', sube ? `Ver ${sube[0]}` : '', sube ? sube[0] : '') : '',
    compara ? k('Baja más', baja ? esc(recorta(baja[0], 22)) : '—', baja ? `▼ ${-baja[1]} puestos` : '', 'rojo', baja ? `Ver ${baja[0]}` : '', baja ? baja[0] : '') : '',
    k('Para revisar', String(raros.length), raros.length ? `a más de ${d.umbrales[1]} % de costo` : 'ningún costo imposible',
      raros.length ? 'ambar' : '', raros.map((p) => p[0]).join(', ') || 'Platos del top vendidos a un % de costo imposible: casi siempre un costo mal guardado en el POS'),
  ].join('');
}

// ── La fila de controles ─────────────────────────────────────────────────
function htmlControles(d, st) {
  const porGrupo = new Map(), porSub = new Map();
  d.platos.forEach((p) => {
    const v = p[3].reduce((a, b) => a + b, 0);
    porGrupo.set(p[1], (porGrupo.get(p[1]) || 0) + v);
    porSub.set(p[2], (porSub.get(p[2]) || 0) + v);
  });
  const orden = (m) => [...m].sort((a, b) => b[1] - a[1]).map(([x]) => x);
  const op = (tipo, valor, txt) => `<button type="button" class="${(tipo ? st.ambito && st.ambito[0] === tipo && st.ambito[1] === valor : !st.ambito) ? 'on' : ''}" data-acc="ambito" data-tipo="${tipo}" data-id="${esc(valor)}">${esc(txt)}</button>`;
  const pop = st.menu === 'ambito' ? `<div class="pl-pop pl-lista">${op('', '', 'Toda la carta')}<span class="pl-sep">Grupos</span>${orden(porGrupo).map((g) => op('g', g, g)).join('')}<span class="pl-sep">Subgrupos</span>${orden(porSub).map((x) => op('s', x, x)).join('')}</div>` : '';
  const seg = (lista, actual, acc) => `<div class="pl-seg" role="group">${lista.map(([id, r]) => `<button type="button" class="${actual === id ? 'on' : ''}" data-acc="${acc}" data-id="${id}">${r}</button>`).join('')}</div>`;
  return `${htmlCromo(d.cromo, st)}
    <div class="pl-m"><button type="button" class="pl-mb${st.ambito ? ' on' : ''}" aria-expanded="${st.menu === 'ambito'}" data-acc="menu" data-id="ambito">Dentro de: ${esc(st.ambito ? st.ambito[1] : 'Toda la carta')} <i>▾</i></button>${pop}</div>
    <span class="vp-esp"></span><span class="vp-rot">Medir</span>${seg([['venta', 'Venta'], ['cant', 'Unidades']], st.medida, 'medida')}`;
}
function htmlTabs(d, st) {
  const tops = TOPES.map(([id, r]) => `<button type="button" class="${st.mostrar === id ? 'on' : ''}" data-acc="mostrar" data-id="${id}">${id === 'elegidos' && st.elegidos_p.length ? `${r} · ${st.elegidos_p.length}` : r}</button>`).join('');
  return `${d.cromo ? htmlPestanas(st.tab) : `<div class="pl-tabs" role="tablist">${['Tabla', 'Puestos'].map((t) => `<button type="button" role="tab" aria-selected="${st.tab === t}" class="${st.tab === t ? 'on' : ''}" data-acc="tab" data-id="${t}">${t}</button>`).join('')}</div>`}
    ${st.tab === 'Tabla' ? `<input type="search" data-acc="buscar" value="${esc(st.q)}" placeholder="Buscar un plato" aria-label="Buscar un plato">` : ''}
    <span class="vp-esp"></span><span class="vp-rot">Mostrar</span><div class="pl-seg" role="group" aria-label="Mostrar">${tops}</div>`;
}

// ── El gráfico de puestos ────────────────────────────────────────────────
function htmlPuestos(d, st, c, colores, ancho, alto) {
  const { P, ult, pue, enGraf } = c;
  if (!enGraf.length) return `<div class="vp-vacio">${st.mostrar === 'elegidos' ? 'Todavía no elegiste platos: marcá ☆ en la tabla.' : 'Sin platos que mostrar.'}</div>`;
  const maxp = Math.max(1, ...enGraf.flatMap((p) => P.map((_, i) => pue[i].get(p[0]) || 0)));
  const filasEje = st.mostrar === 'elegidos' ? maxp : Math.min(maxp, d.tope);
  // El ancho y el alto de la caja de verdad: con un viewBox fijo la letra se
  // achica con la caja (#679), y la zona es para usarla.
  const W = Math.max(260, ancho || 340), ROW = Math.max(18, ((alto || 0) - 38) / Math.max(filasEje, 1)), X0 = 36, X1 = Math.max(X0 + 60, W - 240), H = 34 + filasEje * ROW;
  const xs = P.map((_, j) => (P.length === 1 ? (X0 + X1) / 2 : X0 + j * (X1 - X0) / (P.length - 1)));
  const y = (p) => 30 + (p - 1) * ROW;
  const dentro = (p) => p && p <= filasEje;
  let svg = P.map((q, j) => `<text x="${xs[j]}" y="13" text-anchor="middle" class="vp-eje">${esc(q.etq)}</text><line x1="${xs[j]}" y1="20" x2="${xs[j]}" y2="${H - 6}" class="vp-guia"/>`).join('');
  const foco = st.foco;
  enGraf.forEach((p) => {
    const col = colores.get(p[0]), on = p[0] === foco, apagado = foco && !on;
    // Un período fuera del eje corta la línea: no se dibuja cayendo al fondo.
    let tramo = [];
    const cerrar = () => {
      if (tramo.length > 1) svg += `<polyline points="${tramo.map((q) => q.join(',')).join(' ')}" fill="none" stroke="${col}" stroke-width="${on ? 3.5 : 2}" stroke-opacity="${apagado ? 0.3 : 0.9}" stroke-linejoin="round"/>`;
      tramo = [];
    };
    P.forEach((_, i) => { const pp = pue[i].get(p[0]); if (dentro(pp)) tramo.push([xs[i], y(pp)]); else cerrar(); });
    cerrar();
    P.forEach((q, i) => {
      const pp = pue[i].get(p[0]);
      if (dentro(pp)) svg += `<circle cx="${xs[i]}" cy="${y(pp)}" r="${on ? 5.5 : 4}" fill="${col}" fill-opacity="${apagado ? 0.45 : 1}" class="vp-pt" data-acc="foco" data-id="${esc(p[0])}"><title>${esc(p[0])} · ${esc(q.etq)}: ${pp}º</title></circle>`;
    });
    const pu = pue[ult].get(p[0]);
    if (dentro(pu)) svg += `<text x="${xs[xs.length - 1] + 12}" y="${y(pu)}" dominant-baseline="middle" class="vp-rotp${on ? ' on' : ''}" data-acc="foco" data-id="${esc(p[0])}">${pu} · ${esc(recorta(p[0], Math.max(12, Math.floor((W - X1 - 30) / 6.4))))}</text>`;
  });
  return `<svg role="img" aria-label="Puesto de cada plato en cada período" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${svg}</svg>`;
}

// ── La tabla ─────────────────────────────────────────────────────────────
function filasTabla(d, st, c) {
  const q = sinTilde(st.q.trim());
  return c.filas.filter((p) => !q || sinTilde(p[0]).includes(q));
}
function htmlTabla(d, st, c) {
  const { P, pri, ult, m, pue } = c;
  const filas = filasTabla(d, st, c);
  const porDia = (p, i) => (P[i].dias ? p[m][i] / P[i].dias : 0);
  const maxV = Math.max(1e-9, ...filas.flatMap((p) => P.map((_, i) => porDia(p, i))));
  const cuerpo = filas.map((p) => {
    const [mov, tipo] = movimiento(d, pue[pri].get(p[0]), pue[ult].get(p[0]));
    const v = varPorDia(p[m][pri], P[pri].dias, p[m][ult], P[ult].dias);
    const pc = pctCosto(p[5][ult], p[6][ult]);
    const el = st.elegidos_p.includes(p[0]);
    const barras = P.map((qq, i) => `<i style="height:${Math.max(2, porDia(p, i) / maxV * 20)}px;background:${i === ult ? 'var(--accent)' : 'var(--border-lavender)'}" title="${esc(qq.etq)}: ${m === 3 ? soles(p[3][i]) + ' · ' + soles(porDia(p, i)) + ' por día' : num(p[4][i]) + ' unidades'}"></i>`).join('');
    return `<tr class="vp-f${p[0] === st.foco ? ' sel' : ''}" data-acc="foco" data-id="${esc(p[0])}">
      <td class="vp-estrella"><button type="button" class="${el ? 'on' : ''}" data-acc="elegir" data-id="${esc(p[0])}" aria-label="${el ? 'Quitar de' : 'Agregar a'} elegidos" title="${el ? 'Quitar de' : 'Agregar a'} elegidos">${el ? '★' : '☆'}</button></td>
      <td class="vp-plato"><b title="${esc(p[0])}">${esc(p[0])}</b></td>
      <td class="vp-sub" title="${esc(p[2])}">${esc(p[2])}</td>
      <td><div class="vp-barras">${barras}</div></td>
      <td class="num"><b>${m === 3 ? soles(p[3][ult]) : num(p[4][ult])}</b></td>
      <td class="num ${v == null ? 'azul' : v >= 0 ? 'verde' : 'rojo'}">${v == null ? (p[m][ult] > 0 ? 'nuevo' : '—') : signo(v)}</td>
      <td class="num vp-pu">${pue[ult].get(p[0]) ? pue[ult].get(p[0]) + 'º' : '—'} <span class="vp-mov ${tipo}">${mov}</span></td>
      <td class="num"><span class="pill ${nivel(d, pc)}" title="${pc > d.umbrales[1] ? 'Se vendió a un costo imposible: revisar el costo guardado en el POS' : 'Costo ÷ venta neta de ' + esc(P[ult].etq)}">${pc == null ? '—' : pc.toFixed(1) + ' %'}</span></td></tr>`;
  }).join('');
  return `<table><colgroup><col style="width:28px"><col><col style="width:21%"><col style="width:68px"><col style="width:84px"><col style="width:62px"><col style="width:86px"><col style="width:76px"></colgroup>
    <thead><tr><th></th><th>Plato</th><th>Subgrupo</th><th title="${P.map((x) => esc(x.etq)).join(', ')}">${m === 3 ? 'Por día' : 'Unidades'}</th>
      <th class="num">${esc(P[ult].etq)}</th><th class="num" title="${esc(P[pri].etq)} → ${esc(P[ult].etq)}, por día con venta">por día</th>
      <th class="num" title="Cambio de puesto de ${esc(P[pri].etq)} a ${esc(P[ult].etq)}">Puesto</th><th class="num">% costo</th></tr></thead>
    <tbody>${cuerpo || `<tr><td colspan="8" class="vp-vacio">${st.mostrar === 'elegidos' ? 'Marcá ☆ en los platos que quieras comparar.' : 'Ningún plato con ese nombre.'}</td></tr>`}</tbody></table>`;
}
function textoPie(d, st, c) {
  const { P, pri, ult, enAmb, pue } = c, n = filasTabla(d, st, c).length;
  const notas = [`${n} de ${pue[ult].size} platos con venta en ${P[ult].etq}`];
  if (st.mostrar === 'todos' && st.tab === 'Puestos' && c.filas.length > d.tope) notas.push(`el gráfico, los ${d.tope} primeros`);
  if (P.length === 1) notas.push('con un solo período no hay movimiento: elegí otro arriba');
  else {
    notas.push('la variación es por día con venta');
    notas.push(`${enAmb.filter((p) => !pue[pri].get(p[0]) && (pue[ult].get(p[0]) || 1e6) <= d.tope).length} entran al top ${d.tope}`);
  }
  return notas.join(' · ');
}

// ── La ficha del plato ───────────────────────────────────────────────────
function htmlFicha(d, st, c) {
  const { P, pri, ult, m, pue } = c;
  const p = d.platos.find((x) => x[0] === st.foco);
  if (!p) return '<div class="vp-vacio">Elegí un plato en la tabla o en el gráfico.</div>';
  const pc = pctCosto(p[5][ult], p[6][ult]);
  const v = varPorDia(p[m][pri], P[pri].dias, p[m][ult], P[ult].dias);
  const evo = d.evolucion && d.evolucion.nombre === p[0] ? d.evolucion : null;
  const serie = evo ? evo.serie.map(([etq, vd, cd, sel]) => [etq, m === 3 ? vd : cd, sel])
    : P.map((q, i) => [q.etq, q.dias ? p[m][i] / q.dias : 0, true]);
  const maxB = Math.max(1e-9, ...serie.map((s) => s[1]));
  const barras = serie.map(([etq, val, sel]) => `<div class="vp-ev" title="${esc(etq)}: ${m === 3 ? soles(val) : num(val)} por día"><span class="num">${sel ? (m === 3 ? corto(val) : num(val)) : ''}</span><i style="height:${Math.max(1, val / maxB * 80)}%;background:${sel ? 'var(--accent)' : 'var(--border-lavender)'}"></i><em>${sel ? esc(String(etq).split(' ')[0]) : ''}</em></div>`).join('');
  const pu = pue[ult].get(p[0]);
  let aviso = pu ? `En ${P[ult].etq} es ${pu}º de ${st.ambito ? esc(st.ambito[1]) : 'la carta'}` : `No vendió en ${P[ult].etq}`;
  if (v != null && P.length > 1) aviso += ` y ${m === 3 ? 'vende' : 'sale'} ${signo(v)} por día que en ${P[pri].etq}`;
  aviso += '.';
  let cls = '';
  if (pc > d.umbrales[1]) { aviso += ` Se vendió al ${pc.toFixed(0)} % de costo: el costo que guardó el POS al vender no es el de la receta.`; cls = 'rojo'; }
  const el = st.elegidos_p.includes(p[0]);
  const ventaUnidad = p[4][ult] > 0 ? p[3][ult] / p[4][ult] : null;
  return `<div class="vp-fcab"><span>${esc(p[1])} › ${esc(p[2])}</span><h3 title="${esc(p[0])}">${esc(p[0])}</h3></div>
    <div class="vp-cifras"><div><span>Venta · ${esc(P[ult].etq)}</span><b class="num">${soles(p[3][ult])}</b></div>
      <div><span>Unidades</span><b class="num">${num(p[4][ult])}</b></div>
      <div><span>% costo vendido</span><b class="num ${nivel(d, pc)}">${pc == null ? '—' : pc.toFixed(1) + ' %'}</b></div>
      <div><span>Venta por unidad</span><b class="num">${ventaUnidad ? 'S/ ' + ventaUnidad.toFixed(2) : '—'}</b></div></div>
    <div class="vp-frot">${m === 3 ? 'Venta (S/)' : 'Unidades'} por día con venta${evo ? `, cada ${esc(evo.corte)}` : ''}${evo ? '' : ' <span class="vp-cargando">· cargando el corte entero…</span>'}</div>
    <div class="vp-evol">${barras}</div>
    <div class="vp-aviso ${cls}">${aviso}</div>
    <div class="vp-fbot"><button type="button" class="vp-btn" data-acc="elegir" data-id="${esc(p[0])}">${el ? '★ Quitar' : '☆ Elegir'}</button>
      <button type="button" class="vp-btn" data-acc="hora" data-id="${esc(p[0])}" title="Ver a qué hora se vende">A qué hora →</button>
      ${p[7] ? `<button type="button" class="vp-btn" data-acc="carta" data-id="${esc(p[7])}" title="Su costo en Costo de Carta">Su costo →</button>` : ''}</div>`;
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function pintarTabla(raiz, c) {
  const { data: d, st } = raiz.__d;
  const t = raiz.querySelector('.vp-tabla');
  if (t) t.innerHTML = htmlTabla(d, st, c);
  raiz.querySelector('.vp-pie').textContent = textoPie(d, st, c);
}
function dibujar(raiz, solo) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.vp-cuerpo')) {
    raiz.innerHTML = `<div class="vp-ctrl" data-zona="ctrl"></div><div class="vp-kpis" data-zona="kpis"></div><div class="vp-fila" data-zona="tabs"></div>
      <div class="vp-cuerpo"><div class="vp-zona"><div class="vp-z" data-zona="zona"></div><div class="vp-pie"></div></div><div class="vp-ficha" data-zona="ficha"></div></div>`;
  }
  const c = calcular(d, st);
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  if (solo === 'tabla') { pintarTabla(raiz, c); return; }
  if (!st.foco || !d.platos.some((p) => p[0] === st.foco)) st.foco = d.foco;
  const colores = new Map((st.mostrar === 'elegidos' ? st.elegidos_p : c.enGraf.map((p) => p[0])).map((n, i) => [n, PALETA[i % PALETA.length]]));
  z('ctrl').innerHTML = htmlControles(d, st);
  z('kpis').innerHTML = htmlKpis(d, st, c);
  z('tabs').innerHTML = htmlTabs(d, st);
  const zona = z('zona'), y = zona.querySelector('.vp-tabla')?.scrollTop || 0;
  if (st.tab === 'Puestos') {
    zona.className = 'vp-z puestos';
    zona.innerHTML = htmlPuestos(d, st, c, colores, zona.clientWidth, zona.clientHeight);
  } else {
    zona.className = 'vp-z';
    zona.innerHTML = '<div class="vp-tabla"></div>';
    pintarTabla(raiz, c);
    if (solo === 'foco') zona.querySelector('.vp-tabla').scrollTop = y;
  }
  raiz.querySelector('.vp-pie').textContent = textoPie(d, st, c);
  z('ficha').innerHTML = htmlFicha(d, st, c);
}

function recordar(st) { guardarPl({ medida: st.medida, mostrar: st.mostrar, ambito: st.ambito, elegidos: st.elegidos_p, tab: st.tab }); }

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    const st = raiz.__d.st;
    if (st.menu && !ev.target.closest('.pl-pop') && !(b && b.dataset.acc === 'menu')) { st.menu = null; soltarMeses(raiz); if (!b) { dibujar(raiz, 'foco'); return; } }
    if (!b || !raiz.contains(b) || b.tagName === 'INPUT') return;
    const { data: d } = raiz.__d, id = b.dataset.id, acc = b.dataset.acc;
    if (accionCromo(raiz, acc, id, () => { raiz.querySelector('[data-zona="ctrl"]').innerHTML = htmlControles(d, st); })) return;
    if (acc === 'foco') {
      if (st.foco === id) return;
      st.foco = id;
      dibujar(raiz, 'foco');
      raiz.__d.enviar('foco', id);
      return;
    }
    if (acc === 'hora') { raiz.__d.enviar('hora', { plato: id, n: Date.now() }); return; }
    if (acc === 'carta') { raiz.__d.enviar('carta', { cod: id, n: Date.now() }); return; }
    if (acc === 'tab') {
      if (id === 'Menu') { pedirCromo(raiz, { vista: 'Ingeniería de menú' }); return; }
      st.tab = id;
    } else if (acc === 'elegir') {
      ev.stopPropagation();
      if (st.elegidos_p.includes(id)) st.elegidos_p = st.elegidos_p.filter((x) => x !== id);
      else if (st.elegidos_p.length < d.max_elegidos) st.elegidos_p = st.elegidos_p.concat([id]);
    } else if (acc === 'ambito') { st.ambito = b.dataset.tipo ? [b.dataset.tipo, id] : null; st.menu = null; }
    else if (acc === 'medida') st.medida = id;
    else if (acc === 'mostrar') st.mostrar = id;
    else return;
    recordar(st);
    dibujar(raiz, 'foco');
  });
  // Otro ancho, otro gráfico de puestos (se dibuja al ancho de su caja).
  let espera = null;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => dibujar(raiz, 'foco'), 150); });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    dibujar(raiz, 'tabla');
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.platos || !data.periodos || !data.periodos.length) return;
  let raiz = parentElement.querySelector('.vp');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'vp';
    parentElement.appendChild(raiz);
    const guardado = leerPl({});
    raiz.__d = { st: { medida: guardado.medida || 'venta', mostrar: guardado.mostrar || '15', ambito: guardado.ambito || null,
      elegidos_p: guardado.elegidos || [], tab: guardado.tab === 'Puestos' ? 'Puestos' : 'Tabla', q: '', foco: null, menu: null, elegidos: [] } };
    enlazar(raiz);
  }
  const st = raiz.__d.st;
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.data = data;
  recibirCromo(raiz, data);
  if (st.ambito && !data.platos.some((p) => (st.ambito[0] === 'g' ? p[1] : p[2]) === st.ambito[1])) st.ambito = null;
  if (!st.foco || !data.platos.some((p) => p[0] === st.foco)) st.foco = data.foco;
  dibujar(raiz);
}
