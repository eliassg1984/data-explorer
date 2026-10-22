// Ventas › «Análisis de platos» › Ranking (regla #699).
//
// La monta graficos/ventas_platos.py::_pieza_ranking con st.components.v2
// (sin iframe, estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/Lzua6AASjVigJ8GJktVwM8): los indicadores,
// «Dentro de», Venta | Unidades, el top, el gráfico de puestos, la tabla
// con la venta por día de cada período en barritas, y la ficha del plato.
// El corte y los períodos siguen en Python (cargan datos); todo lo demás
// se resuelve acá sin una corrida. Vuelven a Python: `foco` (el plato
// elegido: su evolución en todo el corte se carga allá), `hora` y `carta`.
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
// `tope` y `max_elegidos`.

const CLAVE = 'vt_pl_est';
const PALETA = ['#6c5ce7', '#0e9fb8', '#e85ba8', '#d97706', '#16a34a', '#9385ec', '#c2410c', '#4938b8', '#0f766e', '#be185d'];
const TOPES = [['10', 'Top 10'], ['15', 'Top 15'], ['20', 'Top 20'], ['todos', 'Todos'], ['elegidos', 'Elegidos']];
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const soles = (v) => `S/ ${Math.round(v).toLocaleString('en-US')}`;
const corto = (v) => (Math.abs(v) >= 1000 ? `S/ ${(v / 1000).toFixed(1)}k` : `S/ ${Math.round(v)}`);
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
  if (st.mostrar === 'elegidos') filas = orden.filter((p) => st.elegidos.includes(p[0]));
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
  const entran = nombres.filter((x) => !pue[pri].get(x) && (pue[ult].get(x) || 1e6) <= d.tope).length;
  const raros = enAmb.filter((p) => (pue[ult].get(p[0]) || 1e6) <= d.tope && pctCosto(p[5][ult], p[6][ult]) > d.umbrales[1]);
  const amb = st.ambito ? st.ambito[1] : 'toda la carta';
  const k = (rot, val, sub, cls = '', tip = '') => `<div class="vp-kpi" title="${esc(tip || rot)}"><span class="vp-kpi-rot">${esc(rot)}</span>
    <span class="vp-kpi-lin"><span class="vp-kpi-val ${cls}">${val}</span><span class="vp-kpi-sub">${sub}</span></span></div>`;
  const compara = P.length > 1;
  return [
    k(`Platos con venta · ${P[ult].etq}`, String(pue[ult].size), `en ${esc(amb)}`),
    compara ? k(`${amb.charAt(0).toUpperCase() + amb.slice(1)} por día`, g == null ? '—' : signo(g),
      `${st.medida === 'cant' ? num(tot(pri) / P[pri].dias) : soles(tot(pri) / P[pri].dias)} → ${st.medida === 'cant' ? num(tot(ult) / P[ult].dias) : soles(tot(ult) / P[ult].dias)}`,
      g == null ? '' : g >= 0 ? 'verde' : 'rojo', `Por día con venta, de ${P[pri].etq} a ${P[ult].etq}: la vara con que se mide cada plato`) : '',
    compara ? k('Sube más', sube ? esc(recorta(sube[0], 22)) : '—', sube ? `▲ ${sube[1]}` : '', 'verde') : '',
    compara ? k('Baja más', baja ? esc(recorta(baja[0], 22)) : '—', baja ? `▼ ${-baja[1]}` : '', 'rojo') : '',
    compara ? k(`Entran al top ${d.tope}`, String(entran), `no vendían en ${P[pri].etq}`) : '',
    k('Para revisar', String(raros.length), raros.length ? `vendidos a más de ${d.umbrales[1]} % de costo` : 'ningún costo imposible',
      raros.length ? 'ambar' : '', raros.map((p) => p[0]).join(', ') || 'Platos del top vendidos a un % de costo imposible: casi siempre un costo mal guardado en el POS'),
  ].join('');
}

// ── Los controles de la pieza ────────────────────────────────────────────
function htmlControles(d, st) {
  const porGrupo = new Map(), porSub = new Map();
  d.platos.forEach((p) => {
    const v = p[3].reduce((a, b) => a + b, 0);
    porGrupo.set(p[1], (porGrupo.get(p[1]) || 0) + v);
    porSub.set(p[2], (porSub.get(p[2]) || 0) + v);
  });
  const grupos = [...porGrupo].sort((a, b) => b[1] - a[1]).map(([g]) => g);
  const subs = [...porSub].sort((a, b) => b[1] - a[1]).map(([s]) => s);
  const chip = (on, acc, id, txt) => `<button type="button" class="vp-chip${on ? ' on' : ''}" data-acc="${acc}" data-id="${esc(id)}">${esc(txt)}</button>`;
  const seg = (lista, actual, acc) => `<div class="vp-seg" role="group">${lista.map(([id, r]) => `<button type="button" class="${actual === id ? 'on' : ''}" data-acc="${acc}" data-id="${id}">${r}</button>`).join('')}</div>`;
  const fijos = grupos.slice(0, 4);
  const enSel = st.ambito && !(st.ambito[0] === 'g' && fijos.includes(st.ambito[1])) ? st.ambito : null;
  return `<div class="vp-fila"><span class="vp-rot">Dentro de</span>${chip(!st.ambito, 'ambito', '', 'Toda la carta')}
      ${fijos.map((g) => chip(st.ambito && st.ambito[0] === 'g' && st.ambito[1] === g, 'grupo', g, g)).join('')}
      <select data-acc="sub" aria-label="Otro grupo o un subgrupo" class="${enSel ? 'on' : ''}"><option value="">${enSel ? (enSel[0] === 'g' ? 'Grupo: ' : 'Subgrupo: ') + esc(enSel[1]) : 'Otro grupo o subgrupo…'}</option>
        ${grupos.length > 4 ? `<optgroup label="Grupos">${grupos.slice(4).map((g) => `<option value="g|${esc(g)}">${esc(g)}</option>`).join('')}</optgroup>` : ''}
        <optgroup label="Subgrupos">${subs.map((x) => `<option value="s|${esc(x)}">${esc(x)}</option>`).join('')}</optgroup></select></div>
    <div class="vp-fila vp-der">${seg([['venta', 'Venta'], ['cant', 'Unidades']], st.medida, 'medida')}${seg(TOPES.map(([id, r]) => [id, id === 'elegidos' ? `${r}${st.elegidos.length ? ' · ' + st.elegidos.length : ''}` : r]), st.mostrar, 'mostrar')}</div>`;
}

// ── El gráfico de puestos ────────────────────────────────────────────────
function htmlPuestos(d, st, c, colores, ancho) {
  const { P, ult, pue, enGraf } = c;
  if (!enGraf.length) return `<div class="vp-vacio">${st.mostrar === 'elegidos' ? 'Todavía no elegiste platos: marcá ☆ en la tabla.' : 'Sin platos que mostrar.'}</div>`;
  const maxp = Math.max(1, ...enGraf.flatMap((p) => P.map((_, i) => pue[i].get(p[0]) || 0)));
  const filasEje = st.mostrar === 'elegidos' ? maxp : Math.min(maxp, d.tope);
  // El ancho de la caja de verdad: con un viewBox fijo la letra se achica
  // con la caja (#679).
  const W = Math.max(260, ancho || 340), ROW = 21, X0 = 26, X1 = Math.max(X0 + 60, W - 150), H = 34 + filasEje * ROW;
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
      if (tramo.length > 1) svg += `<polyline points="${tramo.map((q) => q.join(',')).join(' ')}" fill="none" stroke="${col}" stroke-width="${on ? 3.5 : 2}" stroke-opacity="${apagado ? 0.25 : 0.9}" stroke-linejoin="round"/>`;
      tramo = [];
    };
    P.forEach((_, i) => { const pp = pue[i].get(p[0]); if (dentro(pp)) tramo.push([xs[i], y(pp)]); else cerrar(); });
    cerrar();
    P.forEach((q, i) => {
      const pp = pue[i].get(p[0]);
      if (dentro(pp)) svg += `<circle cx="${xs[i]}" cy="${y(pp)}" r="${on ? 5 : 3.5}" fill="${col}" fill-opacity="${apagado ? 0.35 : 1}" class="vp-pt" data-acc="foco" data-id="${esc(p[0])}"><title>${esc(p[0])} · ${esc(q.etq)}: ${pp}º</title></circle>`;
    });
    const pu = pue[ult].get(p[0]);
    if (dentro(pu)) svg += `<text x="${xs[xs.length - 1] + 10}" y="${y(pu)}" dominant-baseline="middle" class="vp-rotp${on ? ' on' : ''}" data-acc="foco" data-id="${esc(p[0])}">${pu} · ${esc(recorta(p[0], Math.max(12, Math.floor((W - X1 - 30) / 6))))}</text>`;
  });
  return `<svg role="img" aria-label="Puesto de cada plato en cada período" viewBox="0 0 ${W} ${H}" width="100%">${svg}</svg>`;
}

// ── La tabla ─────────────────────────────────────────────────────────────
function htmlTabla(d, st, c, colores) {
  const { P, pri, ult, m, pue } = c;
  const q = sinTilde(st.q.trim());
  const filas = c.filas.filter((p) => !q || sinTilde(p[0]).includes(q));
  const porDia = (p, i) => (P[i].dias ? p[m][i] / P[i].dias : 0);
  const maxV = Math.max(1e-9, ...filas.flatMap((p) => P.map((_, i) => porDia(p, i))));
  const cuerpo = filas.map((p) => {
    const [mov, tipo] = movimiento(d, pue[pri].get(p[0]), pue[ult].get(p[0]));
    const v = varPorDia(p[m][pri], P[pri].dias, p[m][ult], P[ult].dias);
    const pc = pctCosto(p[5][ult], p[6][ult]);
    const el = st.elegidos.includes(p[0]);
    const barras = P.map((qq, i) => `<i style="height:${Math.max(2, porDia(p, i) / maxV * 24)}px;background:${i === ult ? colores.get(p[0]) || 'var(--accent)' : 'var(--border-lavender)'}" title="${esc(qq.etq)}: ${m === 3 ? soles(p[3][i]) + ' · ' + soles(porDia(p, i)) + ' por día' : num(p[4][i]) + ' unidades'}"></i>`).join('');
    return `<tr class="vp-f${p[0] === st.foco ? ' sel' : ''}" data-acc="foco" data-id="${esc(p[0])}">
      <td class="vp-estrella"><button type="button" class="${el ? 'on' : ''}" data-acc="elegir" data-id="${esc(p[0])}" aria-label="${el ? 'Quitar de' : 'Agregar a'} elegidos" title="${el ? 'Quitar de' : 'Agregar a'} elegidos">${el ? '★' : '☆'}</button></td>
      <td class="vp-plato"><div><i style="background:${colores.get(p[0]) || 'var(--border)'}"></i><b title="${esc(p[0])}">${esc(p[0])}</b></div><span>${esc(p[2])}</span></td>
      <td><div class="vp-barras">${barras}</div></td>
      <td class="num"><b>${m === 3 ? soles(p[3][ult]) : num(p[4][ult])}</b></td>
      <td class="num ${v == null ? 'azul' : v >= 0 ? 'verde' : 'rojo'}">${v == null ? (p[m][ult] > 0 ? 'nuevo' : '—') : signo(v)}</td>
      <td class="num vp-pu">${pue[ult].get(p[0]) ? pue[ult].get(p[0]) + 'º' : '—'} <span class="vp-mov ${tipo}">${mov}</span></td>
      <td class="num"><span class="pill ${nivel(d, pc)}" title="${pc > d.umbrales[1] ? 'Se vendió a un costo imposible: revisar el costo guardado en el POS' : 'Costo ÷ venta neta de ' + esc(P[ult].etq)}">${pc == null ? '—' : pc.toFixed(1) + ' %'}</span></td></tr>`;
  }).join('');
  const notas = [`${filas.length} platos`];
  if (st.mostrar === 'todos' && filas.length > d.tope) notas.push(`el gráfico, los ${d.tope} primeros`);
  if (P.length === 1) notas.push('con un solo período no hay movimiento: elegí otro arriba');
  notas.push('la variación es por día con venta');
  return `<div class="vp-tcab"><input type="search" data-acc="buscar" value="${esc(st.q)}" placeholder="Buscar un plato" aria-label="Buscar un plato"></div>
    <div class="vp-tabla"><table><thead><tr><th></th><th>Plato</th><th title="${P.map((x) => esc(x.etq)).join(', ')}">${m === 3 ? 'Por día' : 'Unidades'}</th>
      <th class="num">${esc(P[ult].etq)}</th><th class="num" title="${esc(P[pri].etq)} → ${esc(P[ult].etq)}, por día con venta">por día</th>
      <th class="num" title="Cambio de puesto de ${esc(P[pri].etq)} a ${esc(P[ult].etq)}">Puesto</th><th class="num">% costo</th></tr></thead>
      <tbody>${cuerpo || `<tr><td colspan="7" class="vp-vacio">${st.mostrar === 'elegidos' ? 'Marcá ☆ en los platos que quieras comparar.' : 'Ningún plato con ese nombre.'}</td></tr>`}</tbody></table></div>
    <div class="vp-pie">${notas.join(' · ')}</div>`;
}

// ── La ficha del plato ───────────────────────────────────────────────────
function htmlFicha(d, st, c, colores) {
  const { P, pri, ult, m, pue } = c;
  const p = d.platos.find((x) => x[0] === st.foco);
  if (!p) return '<div class="vp-vacio">Elegí un plato en el gráfico o en la tabla.</div>';
  const pc = pctCosto(p[5][ult], p[6][ult]);
  const v = varPorDia(p[m][pri], P[pri].dias, p[m][ult], P[ult].dias);
  const col = colores.get(p[0]) || 'var(--accent)';
  const evo = d.evolucion && d.evolucion.nombre === p[0] ? d.evolucion : null;
  const serie = evo ? evo.serie.map(([etq, vd, cd, sel]) => [etq, m === 3 ? vd : cd, sel])
    : P.map((q, i) => [q.etq, q.dias ? p[m][i] / q.dias : 0, true]);
  const maxB = Math.max(1e-9, ...serie.map((s) => s[1]));
  const barras = serie.map(([etq, val, sel]) => `<div class="vp-ev" title="${esc(etq)}: ${m === 3 ? corto(val) : num(val)} por día"><span class="num">${sel ? (m === 3 ? corto(val) : num(val)) : ''}</span><i style="height:${Math.max(2, val / maxB * 76)}px;background:${sel ? col : 'var(--border-lavender)'}"></i><em>${sel ? esc(String(etq).split(' ')[0]) : ''}</em></div>`).join('');
  const pu = pue[ult].get(p[0]);
  let aviso = pu ? `En ${P[ult].etq} es ${pu}º de ${st.ambito ? esc(st.ambito[1]) : 'la carta'}` : `No vendió en ${P[ult].etq}`;
  if (v != null && P.length > 1) aviso += ` y ${m === 3 ? 'vende' : 'sale'} ${signo(v)} por día que en ${P[pri].etq}`;
  aviso += '.';
  let cls = '';
  if (pc > d.umbrales[1]) { aviso += ` Se vendió al ${pc.toFixed(0)} % de costo: el costo que guardó el POS al vender no es el de la receta. Mirá su costo en Costo de Carta.`; cls = 'rojo'; }
  const el = st.elegidos.includes(p[0]);
  const ventaUnidad = p[4][ult] > 0 ? p[3][ult] / p[4][ult] : null;
  return `<div class="vp-fcab"><span>${esc(p[1])} › ${esc(p[2])}</span><h3>${esc(p[0])}</h3></div>
    <div class="vp-cifras"><div><span>Venta · ${esc(P[ult].etq)}</span><b class="num">${soles(p[3][ult])}</b></div>
      <div><span>Unidades</span><b class="num">${num(p[4][ult])}</b></div>
      <div><span>% costo vendido</span><b class="num ${nivel(d, pc)}">${pc == null ? '—' : pc.toFixed(1) + ' %'}</b></div>
      <div><span>Venta por unidad</span><b class="num">${ventaUnidad ? 'S/ ' + ventaUnidad.toFixed(2) : '—'}</b></div></div>
    <div class="vp-frot">${m === 3 ? 'Venta' : 'Unidades'} por día con venta${evo ? `, cada ${esc(evo.corte)} del corte` : ''}${evo ? '' : ' <span class="vp-cargando">· cargando el corte entero…</span>'}</div>
    <div class="vp-evol">${barras}</div>
    <div class="vp-aviso ${cls}">${aviso}</div>
    <div class="vp-fbot"><button type="button" class="vp-btn" data-acc="elegir" data-id="${esc(p[0])}">${el ? 'Quitar de elegidos' : 'Agregar a elegidos'}</button>
      <button type="button" class="vp-btn" data-acc="hora" data-id="${esc(p[0])}">A qué hora se vende →</button>
      ${p[7] ? `<button type="button" class="vp-btn" data-acc="carta" data-id="${esc(p[7])}">Su costo en Costo de Carta →</button>` : ''}</div>`;
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz, solo) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.vp-cuerpo')) {
    raiz.innerHTML = `<div class="vp-kpis" data-zona="kpis"></div><div class="vp-ctrl" data-zona="ctrl"></div>
      <div class="vp-cuerpo"><div class="vp-caja vp-g" data-zona="puestos"></div><div class="vp-caja vp-t" data-zona="tabla"></div><div class="vp-caja vp-ficha" data-zona="ficha"></div></div>`;
  }
  const c = calcular(d, st);
  const colores = new Map((st.mostrar === 'elegidos' ? st.elegidos : c.enGraf.map((p) => p[0])).map((n, i) => [n, PALETA[i % PALETA.length]]));
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  z('kpis').innerHTML = htmlKpis(d, st, c);
  z('ctrl').innerHTML = htmlControles(d, st);
  z('puestos').innerHTML = htmlPuestos(d, st, c, colores, z('puestos').clientWidth - 16);
  const t = z('tabla');
  if (solo === 'tabla') {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlTabla(d, st, c, colores);
    t.querySelector('.vp-tabla').replaceWith(tmp.querySelector('.vp-tabla'));
    t.querySelector('.vp-pie').replaceWith(tmp.querySelector('.vp-pie'));
  } else {
    const y = t.querySelector('.vp-tabla')?.scrollTop || 0;
    t.innerHTML = htmlTabla(d, st, c, colores);
    if (solo === 'foco') t.querySelector('.vp-tabla').scrollTop = y;
  }
  z('ficha').innerHTML = htmlFicha(d, st, c, colores);
}

function recordar(st) { guardar(CLAVE, { medida: st.medida, mostrar: st.mostrar, ambito: st.ambito, elegidos: st.elegidos }); }

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.tagName === 'SELECT' || b.tagName === 'INPUT') return;
    const { data: d, st } = raiz.__d, id = b.dataset.id, acc = b.dataset.acc;
    if (acc === 'foco') {
      if (st.foco === id) return;
      st.foco = id;
      dibujar(raiz, 'foco');
      raiz.__d.enviar('foco', id);
      return;
    }
    if (acc === 'hora') { raiz.__d.enviar('hora', { plato: id, n: Date.now() }); return; }
    if (acc === 'carta') { raiz.__d.enviar('carta', { cod: id, n: Date.now() }); return; }
    if (acc === 'elegir') {
      ev.stopPropagation();
      if (st.elegidos.includes(id)) st.elegidos = st.elegidos.filter((x) => x !== id);
      else if (st.elegidos.length < d.max_elegidos) st.elegidos = st.elegidos.concat([id]);
    } else if (acc === 'ambito') st.ambito = null;
    else if (acc === 'grupo') st.ambito = st.ambito && st.ambito[0] === 'g' && st.ambito[1] === id ? null : ['g', id];
    else if (acc === 'medida') st.medida = id;
    else if (acc === 'mostrar') st.mostrar = id;
    else return;
    recordar(st);
    dibujar(raiz, 'foco');
  });
  raiz.addEventListener('change', (ev) => {
    if (ev.target.dataset.acc !== 'sub') return;
    const st = raiz.__d.st;
    st.ambito = ev.target.value ? ev.target.value.split('|') : null;
    recordar(st);
    dibujar(raiz);
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
    raiz.__d = { st: Object.assign({ medida: 'venta', mostrar: '15', ambito: null, elegidos: [], q: '', foco: null }, leer(CLAVE, {})) };
    enlazar(raiz);
  }
  const st = raiz.__d.st;
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.data = data;
  const nombres = new Set(data.platos.map((p) => p[0]));
  if (st.ambito && !data.platos.some((p) => (st.ambito[0] === 'g' ? p[1] : p[2]) === st.ambito[1])) st.ambito = null;
  if (!st.foco || !nombres.has(st.foco)) st.foco = data.foco;
  dibujar(raiz);
}
