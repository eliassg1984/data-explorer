// Ventas › «Análisis de platos» › Ingeniería de menú (regla #700).
//
// La monta graficos/ventas_menu.py::vista_ingenieria con st.components.v2.
// Es la forma del boceto aprobado
// (https://claude.ai/artifact/Lzua6AASjVigJ8GJktVwM8): las cifras por clase
// y los cuatro cuadros, ubicados como en la matriz —arriba lo que deja más,
// a la derecha lo que se pide más—, más la matriz y la tabla, que se eligen
// acá sin una corrida. LA CUENTA NO ESTÁ ACÁ: `clasificar` corre en Python y
// cada plato llega con su clase; esto sólo la muestra.
//
// Python manda en `data`: `platos` ([nombre, subgrupo, clase, unidades,
// % unidades, pedidos, % pedidos, precio neto, costo, % costo, margen/plato,
// margen total, al límite, clase con pedidos, clase antes]), `resumen`,
// `fuera`, `etq`, `etq_ant`, `dias`, los textos de cada clase y los
// umbrales del % de costo.

const CLAVE = 'vt_ing_est';
const ORDEN = ['rompecabezas', 'estrella', 'perro', 'caballo'];
const COLOR = { estrella: 'var(--success)', caballo: 'var(--warning)', rompecabezas: 'var(--accent)', perro: 'var(--danger)' };
const F = { nom: 0, sub: 1, clase: 2, u: 3, mm: 4, ped: 5, mmped: 6, precio: 7, costo: 8, pct: 9, margen: 10, mtot: 11, limite: 12, cped: 13, antes: 14 };
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const soles = (v, dec = 2) => (v == null ? '—' : `S/ ${Number(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec })}`);
const pct = (v, dec = 1) => (v == null ? '—' : `${(v * 100).toFixed(dec)} %`);
const num = (v) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }));
function nivel(d, p) { if (p == null) return ''; const x = p * 100; return x > d.umbrales_costo[1] ? 'rojo' : x > d.umbrales_costo[0] ? 'ambar' : ''; }

function chips(d, p) {
  let h = '';
  if (p[F.limite]) h += '<span class="ig-chip lim" title="A menos de 5 % de un umbral: su clase puede cambiar con poco">al límite</span>';
  if (p[F.cped] && p[F.cped] !== p[F.clase]) h += `<span class="ig-chip" title="Si cada pedido contara una vez">con pedidos: ${esc(d.singular[p[F.cped]].toLowerCase())}</span>`;
  if (p[F.antes] && p[F.antes] !== p[F.clase]) h += `<span class="ig-chip ant" title="Su clase en ${esc(d.etq_ant)}">antes: ${esc(d.singular[p[F.antes]].toLowerCase())}</span>`;
  return h;
}

function htmlKpis(d, st) {
  const r = d.resumen;
  return ['estrella', 'caballo', 'rompecabezas', 'perro'].map((k) => {
    const c = r.clases[k], parte = r.margen ? c.margen / r.margen : 0;
    return `<button type="button" class="ig-kpi ${k}${st.clase === k ? ' on' : ''}" data-acc="clase" data-id="${k}" title="${esc(d.detalle[k])} ${esc(d.accion[k])}.">
      <span class="ig-kpi-rot"><i></i>${esc(d.nombres[k])}</span>
      <span class="ig-kpi-lin"><b class="num">${c.n}</b><span>${pct(parte, 0)} del margen</span></span></button>`;
  }).join('');
}

function htmlTexto(d) {
  const r = d.resumen;
  return `Se clasifica <b>${esc(d.etq)}</b>, el último período elegido${d.etq_ant ? ` (y «antes» es ${esc(d.etq_ant)})` : ''} ·
    ${d.dias} días con venta · ${r.n} platos, ${num(r.u)} unidades, ${soles(r.margen, 0)} de margen.
    <b>Popular</b>: ${pct(r.umbral)} o más de las unidades (70 % × 1/${r.n}). <b>Deja mucho</b>: ${soles(r.acm)} o más por plato.`;
}

// ── Cuadros ──────────────────────────────────────────────────────────────
function htmlCuadros(d) {
  const r = d.resumen, conPed = r.pedidos != null;
  const cuadro = (k) => {
    const ps = d.platos.filter((p) => p[F.clase] === k), c = r.clases[k];
    const filas = ps.map((p) => `<li><span class="ig-nom"><b title="${esc(p[F.nom])} · ${esc(p[F.sub])}">${esc(p[F.nom])}</b>${chips(d, p)}</span>
        <span class="num">${soles(p[F.margen])}</span><span class="num suave">${num(p[F.u])} u</span>${conPed ? `<span class="num suave">${num(p[F.ped])} ped.</span>` : ''}</li>`).join('');
    return `<div class="ig-cuadro ${k}"><div class="ig-ctit"><b>${esc(d.nombres[k])}</b><span>${c.n} ${c.n === 1 ? 'plato' : 'platos'} · ${pct(r.margen ? c.margen / r.margen : 0, 0)} del margen</span></div>
      <div class="ig-acc"><b>${esc(d.accion[k])}</b> · ${esc(d.detalle[k])}</div>
      ${ps.length ? `<ul class="ig-filas${conPed ? ' ped' : ''}"><li class="ig-cols"><span></span><span>margen/plato</span><span>unid.</span>${conPed ? '<span>pedidos</span>' : ''}</li>${filas}</ul>` : '<div class="ig-vacio">Ninguno en este período.</div>'}</div>`;
  };
  return `<div class="ig-cuadros"><span class="ig-eje-y">deja más por plato ↑</span>${ORDEN.map(cuadro).join('')}<span class="ig-eje-x">se pide más →</span></div>`;
}

// ── Matriz ───────────────────────────────────────────────────────────────
function htmlMatriz(d, ancho) {
  const r = d.resumen, ps = d.platos;
  const W = Math.max(420, ancho || 800), H = 420, L = 54, R = 16, T = 14, B = 34;
  const xMax = Math.max(r.umbral * 1.6, ...ps.map((p) => p[F.mm])) * 1.08;
  const yMax = Math.max(r.acm * 1.6, ...ps.map((p) => p[F.margen])) * 1.08;
  const x = (v) => L + v / xMax * (W - L - R), y = (v) => T + (1 - v / yMax) * (H - T - B);
  const ux = x(r.umbral), uy = y(r.acm);
  let svg = `<rect x="${ux}" y="${T}" width="${W - R - ux}" height="${uy - T}" class="q estrella"/><rect x="${L}" y="${T}" width="${ux - L}" height="${uy - T}" class="q rompecabezas"/>
    <rect x="${L}" y="${uy}" width="${ux - L}" height="${H - B - uy}" class="q perro"/><rect x="${ux}" y="${uy}" width="${W - R - ux}" height="${H - B - uy}" class="q caballo"/>
    <line x1="${ux}" y1="${T}" x2="${ux}" y2="${H - B}" class="umbral"/><line x1="${L}" y1="${uy}" x2="${W - R}" y2="${uy}" class="umbral"/>
    <text x="${W - R - 4}" y="${T + 14}" text-anchor="end" class="qrot">${esc(d.nombres.estrella)}</text><text x="${L + 4}" y="${T + 14}" class="qrot">${esc(d.nombres.rompecabezas)}</text>
    <text x="${L + 4}" y="${H - B - 6}" class="qrot">${esc(d.nombres.perro)}</text><text x="${W - R - 4}" y="${H - B - 6}" text-anchor="end" class="qrot">${esc(d.nombres.caballo)}</text>
    <text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" class="eje">Parte de las unidades (popularidad) →</text>
    <text x="14" y="${(T + H - B) / 2}" text-anchor="middle" class="eje" transform="rotate(-90 14 ${(T + H - B) / 2})">Margen por plato →</text>
    <text x="${ux}" y="${H - B + 14}" text-anchor="middle" class="eje">${pct(r.umbral)}</text><text x="${L - 6}" y="${uy + 4}" text-anchor="end" class="eje">${soles(r.acm, 0)}</text>`;
  // Los nombres: el que más deja primero, donde no pise otro ni un punto.
  const cajas = ps.map((p) => [x(p[F.mm]) - 5, y(p[F.margen]) - 5, 10, 10]);
  const choca = (a, b) => a[0] < b[0] + b[2] && b[0] < a[0] + a[2] && a[1] < b[1] + b[3] && b[1] < a[1] + a[3];
  const puestas = [];
  ps.forEach((p) => {
    svg += `<circle cx="${x(p[F.mm])}" cy="${y(p[F.margen])}" r="5" class="pt ${p[F.clase]}"><title>${esc(p[F.nom])} · ${esc(d.singular[p[F.clase]])} · ${num(p[F.u])} u (${pct(p[F.mm])}) · ${soles(p[F.margen])} por plato</title></circle>`;
  });
  ps.forEach((p, i) => {
    const t = p[F.nom].length > 22 ? `${p[F.nom].slice(0, 21)}…` : p[F.nom], w = t.length * 5.8 + 4, h = 12;
    const px = x(p[F.mm]), py = y(p[F.margen]);
    for (const [bx, by, anc] of [[px + 7, py - h / 2, 'start'], [px - 7 - w, py - h / 2, 'start'], [px - w / 2, py - 8 - h, 'start'], [px - w / 2, py + 8, 'start']]) {
      const caja = [bx, by, w, h];
      if (bx < L || bx + w > W - R || by < T || by + h > H - B) continue;
      if (puestas.some((o) => choca(caja, o)) || cajas.some((c, j) => j !== i && choca(caja, c))) continue;
      puestas.push(caja);
      svg += `<text x="${bx + 2}" y="${by + h - 2}" text-anchor="${anc}" class="nom">${esc(t)}</text>`;
      break;
    }
  });
  return `<svg role="img" aria-label="Matriz de popularidad y margen" viewBox="0 0 ${W} ${H}" width="100%">${svg}</svg>`;
}

// ── Tabla ────────────────────────────────────────────────────────────────
const COLS = [['nom', 'Plato', ''], ['clase', 'Clase', ''], ['u', 'Unid.', 'num'], ['mm', '% unid.', 'num'], ['ped', 'Pedidos', 'num'],
  ['precio', 'Precio neto', 'num'], ['costo', 'Costo', 'num'], ['pct', '% costo', 'num'], ['margen', 'Margen/plato', 'num'], ['mtot', 'Margen total', 'num']];
function htmlTabla(d, st) {
  const k = F[st.orden] ?? F.mtot, dir = st.asc ? 1 : -1;
  const ps = d.platos.filter((p) => !st.clase || p[F.clase] === st.clase).slice()
    .sort((a, b) => { const x = a[k] ?? -1e9, y = b[k] ?? -1e9; return (x < y ? -dir : x > y ? dir : 0); });
  const filas = ps.map((p) => `<tr><td class="ig-nom"><b title="${esc(p[F.sub])}">${esc(p[F.nom])}</b>${chips(d, p)}</td>
      <td><span class="ig-clase ${p[F.clase]}"><i></i>${esc(d.singular[p[F.clase]])}</span></td>
      <td class="num">${num(p[F.u])}</td><td class="num">${pct(p[F.mm])}</td><td class="num">${num(p[F.ped])}</td>
      <td class="num">${soles(p[F.precio])}</td><td class="num">${soles(p[F.costo])}</td><td class="num"><span class="pill ${nivel(d, p[F.pct])}">${pct(p[F.pct])}</span></td>
      <td class="num">${soles(p[F.margen])}</td><td class="num"><b>${soles(p[F.mtot], 0)}</b></td></tr>`).join('');
  return `<div class="ig-tabla"><table><thead><tr>${COLS.map(([id, r, c]) => `<th class="${c}"><button type="button" data-acc="orden" data-id="${id}" class="${st.orden === id ? 'on' : ''}">${r}${st.orden === id ? (st.asc ? ' ↑' : ' ↓') : ''}</button></th>`).join('')}</tr></thead>
    <tbody>${filas}</tbody></table></div>${st.clase ? `<div class="ig-filtro">Sólo ${esc(d.nombres[st.clase].toLowerCase())} · <button type="button" data-acc="clase" data-id="${st.clase}">ver todas</button></div>` : ''}`;
}

function dibujar(raiz) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.ig-cab')) {
    raiz.innerHTML = `<div class="ig-cab"><div class="ig-kpis" data-zona="kpis"></div><div class="ig-seg" role="tablist" aria-label="Forma" data-zona="formas"></div></div>
      <div class="ig-texto" data-zona="texto"></div><div class="ig-cuerpo" data-zona="cuerpo"></div><div class="ig-pie" data-zona="pie"></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  z('kpis').innerHTML = htmlKpis(d, st);
  z('formas').innerHTML = [['cuadros', 'Cuadros'], ['matriz', 'Matriz'], ['tabla', 'Tabla']].map(([id, r]) =>
    `<button type="button" role="tab" aria-selected="${st.forma === id}" class="${st.forma === id ? 'on' : ''}" data-acc="forma" data-id="${id}">${r}</button>`).join('');
  z('texto').innerHTML = htmlTexto(d);
  const c = z('cuerpo');
  c.innerHTML = st.forma === 'matriz' ? htmlMatriz(d, c.clientWidth) : st.forma === 'tabla' ? htmlTabla(d, st) : htmlCuadros(d);
  const fuera = d.fuera.map(([p, mo, pr, co]) => `${esc(p)} (${esc(mo)}${mo.startsWith('cuesta') ? `: ${soles(co)} de costo contra ${soles(pr)}` : ''})`);
  z('pie').innerHTML = (fuera.length ? `<b>Fuera</b>: ${fuera.join(' · ')}. ` : '')
    + `<b>Al límite</b>: a menos de 5 % de un corte, en los platos que venden ${num(d.resumen.piso)} unidades o más. Método: Kasavana y Smith (1982), con las fórmulas de AHLEI; «al límite» y «con pedidos» son agregados nuestros.`;
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b)) return;
    const st = raiz.__d.st, id = b.dataset.id;
    if (b.dataset.acc === 'forma') st.forma = id;
    else if (b.dataset.acc === 'clase') { st.clase = st.clase === id ? null : id; if (st.clase) st.forma = 'tabla'; }
    else if (b.dataset.acc === 'orden') { if (st.orden === id) st.asc = !st.asc; else { st.orden = id; st.asc = id === 'nom' || id === 'clase'; } }
    else return;
    guardar(CLAVE, { forma: st.forma });
    dibujar(raiz);
  });
  let espera = null;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => { if (raiz.__d.st.forma === 'matriz') dibujar(raiz); }, 150); });
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.platos) return;
  let raiz = parentElement.querySelector('.ig');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'ig';
    parentElement.appendChild(raiz);
    raiz.__d = { st: Object.assign({ forma: 'cuadros', clase: null, orden: 'mtot', asc: false }, leer(CLAVE, {})) };
    enlazar(raiz);
  }
  raiz.__d.data = data;
  dibujar(raiz);
}
